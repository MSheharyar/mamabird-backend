import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from typing import List, Optional

from app.api.auth import get_current_user
from app.api.dependencies import require_subscription, verify_child_ownership, get_tenant_db
from app.db.client import get_supabase
from app.db.tenant import TenantSafeQuery
from app.services.sanitizer import sanitize_message, check_response_safety
from app.services.redis_client import incr_with_ttl
from app.services.claude_service import chat_with_character
from app.services.message_limit import get_message_limit, check_and_increment_message_count
from app.services.badge_service import check_and_award_badges
from app.config.client_config import get_client_config_by_id, get_client_config_cached
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
    # No age on the profile means we do NOT know the child — assume the young end.
    # Defaulting to 7 (as this did) hands a 3-year-old a Grade 1-2 tutor, which is
    # exactly the "too old" tone that was reported.
    child_age = profile.get("age") or 5
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

    # 5. Load the MOST RECENT sessions (desc), then flatten oldest->newest so the
    #    model sees current context (not the child's very first sessions ever).
    sessions = db.table("chat_sessions").select("messages").eq(
        "child_profile_id", req.child_profile_id
    ).eq("character", req.character).eq("subject", req.subject).order(
        "created_at", desc=True
    ).limit(10).execute()

    history = []
    for session_row in reversed(sessions.data or []):
        msgs = session_row.get("messages") or []
        history.extend(msgs)
    history = history[-20:]

    # 5b. If the child is enrolled in a class, follow the teacher's latest lesson plan
    lesson_plan = None
    if profile.get("classroom_id"):
        lp = db.table("lesson_plans").select("plan_data").eq(
            "classroom_id", profile["classroom_id"]
        ).order("created_at", desc=True).limit(1).execute()
        if lp.data:
            lesson_plan = lp.data[0].get("plan_data")

    # 6. Call Claude
    result = await chat_with_character(
        config=config,
        character=req.character,
        subject=req.subject,
        child_age=child_age,
        conversation_history=history,
        new_message=san["sanitized"],
        child_name=child_name,
        lesson_plan=lesson_plan,
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
        "model": result.get("model", "claude-haiku-4-5"),
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


class DemoMessage(BaseModel):
    role: str
    content: str


class DemoChatRequest(BaseModel):
    message: str
    history: Optional[List[DemoMessage]] = []

    @field_validator("message")
    @classmethod
    def bounded(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("message must be 1–500 characters")
        return v


_DEMO_MSG_LIMIT = 4
_DEMO_WINDOW_SECONDS = 3600  # 1 hour rolling window per IP

_SAFE_FALLBACK = "Tweet tweet! 🐦 Let's keep our spelling adventure going — what word would you like to try next?"


@router.post("/demo")
@limiter.limit("10/minute")
async def demo_chat(request: Request, req: DemoChatRequest):
    """Public Spelling demo — no auth. Chirpy + Spelling, 4 messages/IP/hour via Redis."""

    # 1. Server-side per-IP message cap (Redis / in-memory fallback)
    client_ip = request.client.host if request.client else "unknown"
    redis_key = f"demo:{client_ip}"
    demo_count = incr_with_ttl(redis_key, _DEMO_WINDOW_SECONDS)
    if demo_count > _DEMO_MSG_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "DEMO_LIMIT_REACHED",
                "message": "Free demo limit reached. Sign up for a free 3-month trial to keep learning!",
            },
        )

    # 2. Sanitize incoming message
    san = sanitize_message(req.message)
    if not san["safe"]:
        raise HTTPException(status_code=400, detail="Message contains disallowed content.")

    # 3. Load ThreeBabyBirdies config
    try:
        config = get_client_config_cached("threebabybirdies.com")
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # 4. Sanitize history — run each item through injection scanner, drop failures
    safe_history = []
    for h in (req.history or []):
        if h.role not in ("user", "assistant") or not h.content:
            continue
        h_san = sanitize_message(h.content)
        if h_san["safe"]:
            safe_history.append({"role": h.role, "content": h_san["sanitized"]})
    safe_history = safe_history[-6:]  # last 3 turns

    # 5. Call Claude
    result = await chat_with_character(
        config=config,
        character="character_1",
        subject="spelling",
        child_age=7,
        conversation_history=safe_history,
        new_message=san["sanitized"],
        child_name="friend",
    )

    # 6. Post-generation safety check on Claude's response
    response_text = result.get("response", "")
    safety = check_response_safety(response_text)
    if not safety["safe"]:
        logger.warning("Demo post-gen safety triggered (%s) — returning fallback", safety["reason"])
        response_text = _SAFE_FALLBACK

    remaining = max(0, _DEMO_MSG_LIMIT - demo_count)
    return {
        "response": response_text,
        "fallback": result.get("fallback", False) or not safety["safe"],
        "remaining": remaining,
    }
