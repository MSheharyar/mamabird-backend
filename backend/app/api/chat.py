import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from app.api.auth import get_current_user
from app.api.dependencies import require_subscription, verify_child_ownership, get_tenant_db
from app.db.client import get_supabase
from app.db.tenant import TenantSafeQuery
from app.services.sanitizer import sanitize_message
from app.services.claude_service import chat_with_character
from app.services.message_limit import get_message_limit, check_and_increment_message_count
from app.services.badge_service import check_and_award_badges
from app.config.client_config import get_client_config_by_id
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# chat_sessions schema: id, user_id, child_profile_id, character, subject, messages(JSONB), client_id, created_at
# progress schema:      id, child_profile_id, subject, topic, score, total_questions, session_date, client_id
# usage_logs schema:    id, client_id, user_id, child_profile_id, endpoint, input_tokens, output_tokens,
#                       cost_usd, model, duration_ms, was_fallback, created_at


class ChatRequest(BaseModel):
    child_profile_id: str
    character: str
    subject: str
    message: str

    @field_validator("message")
    @classmethod
    def bounded(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("message must be 1–500 characters")
        return v


@router.post("")
@limiter.limit("15/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    current_user: dict = Depends(require_subscription()),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    # 1. Sanitize incoming message
    san = sanitize_message(req.message)
    if not san["safe"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSAFE_INPUT",
                "message": "Message contains disallowed content.",
                "reason": san["reason"],
            },
        )

    # 2. Verify child profile belongs to user
    profile = await verify_child_ownership(req.child_profile_id, current_user)

    child_name = profile.get("child_name", "friend")
    child_age = profile.get("age", 7) or 7
    client_id = profile.get("client_id")

    if not client_id:
        raise HTTPException(status_code=500, detail="Client configuration not found")

    # 3. Check message limit for this child's subscription tier
    user_row = get_supabase().table("users").select(
        "subscription_status, subscription_plan"
    ).eq("id", current_user["user_id"]).execute()
    user_data = user_row.data[0] if user_row.data else {}
    limit = get_message_limit(
        user_data.get("subscription_status", "trial"),
        user_data.get("subscription_plan"),
    )
    count_result = check_and_increment_message_count(
        req.child_profile_id,
        current_user["user_id"],
        client_id,
        limit,
    )
    if not count_result["allowed"]:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "MESSAGE_LIMIT_REACHED",
                "message": f"Message limit of {limit} reached for this child. Please upgrade your plan.",
                "current": count_result["current"],
                "limit": limit,
            },
        )

    # 4. Load cached client config
    config = get_client_config_by_id(client_id)

    # 5. Load previous session messages (flatten JSONB arrays across recent sessions)
    sessions = db.table("chat_sessions").select("messages").eq(
        "child_profile_id", req.child_profile_id
    ).eq("character", req.character).eq("subject", req.subject).order(
        "created_at", desc=False
    ).limit(10).execute()

    history = []
    for session_row in (sessions.data or []):
        msgs = session_row.get("messages") or []
        history.extend(msgs)
    history = history[-20:]

    # 6. Call Claude
    result = await chat_with_character(
        config=config,
        character=req.character,
        subject=req.subject,
        child_age=child_age,
        conversation_history=history,
        new_message=san["sanitized"],
        child_name=child_name,
    )

    # 7. Save this turn to chat_sessions (one row per turn, messages = [user, assistant])
    turn_messages = [
        {"role": "user", "content": san["sanitized"]},
        {"role": "assistant", "content": result["response"]},
    ]
    new_session = db.table("chat_sessions").insert({
        "user_id": current_user["user_id"],
        "child_profile_id": req.child_profile_id,
        "character": req.character,
        "subject": req.subject,
        "messages": turn_messages,
    }).execute()

    session_id = new_session.data[0]["id"] if new_session.data else None

    # 8. Write progress and check badges if Claude scored
    new_badges = []
    if result.get("progress"):
        p = result["progress"]
        db.table("progress").insert({
            "child_profile_id": req.child_profile_id,
            "subject": req.subject,
            "score": p.get("score", 0),
            "total_questions": p.get("total", 1),
            "topic": p.get("topic", req.subject),
            "session_date": date.today().isoformat(),
        }).execute()
        new_badges = check_and_award_badges(
            req.child_profile_id, client_id, req.subject, p
        )

    # 9. Log usage
    db.table("usage_logs").insert({
        "user_id": current_user["user_id"],
        "child_profile_id": req.child_profile_id,
        "endpoint": "/chat",
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "cost_usd": float(result.get("cost_usd", 0)),
        "model": "claude-sonnet-4-6",
        "duration_ms": result.get("duration_ms", 0),
        "was_fallback": result.get("fallback", False),
    }).execute()

    return {
        "response": result["response"],
        "progress": result.get("progress"),
        "new_badges": new_badges,
        "illustration_key": f"{req.character}_{req.subject}",
        "session_id": session_id,
        "fallback": result.get("fallback", False),
    }
