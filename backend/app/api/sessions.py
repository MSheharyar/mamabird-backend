import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client
from dotenv import load_dotenv

from app.api.auth import get_current_user
from app.api.dependencies import require_subscription, verify_child_ownership

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/{child_profile_id}")
async def list_sessions(
    child_profile_id: str,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(require_subscription()),
):
    await verify_child_ownership(child_profile_id, current_user)

    offset = (page - 1) * limit

    result = supabase.table("chat_sessions").select(
        "id, character, subject, created_at, messages"
    ).eq("child_profile_id", child_profile_id).order(
        "created_at", desc=True
    ).range(offset, offset + limit - 1).execute()

    sessions = []
    for s in (result.data or []):
        msgs = s.get("messages") or []
        sessions.append({
            "id": s["id"],
            "character": s["character"],
            "subject": s["subject"],
            "created_at": s["created_at"],
            "message_count": len(msgs),
        })

    # Get total count
    count_result = supabase.table("chat_sessions").select(
        "id", count="exact"
    ).eq("child_profile_id", child_profile_id).execute()
    total = count_result.count if hasattr(count_result, "count") else len(sessions)

    return {"sessions": sessions, "total": total, "page": page, "limit": limit}


@router.get("/{child_profile_id}/{session_id}")
async def get_session(
    child_profile_id: str,
    session_id: str,
    current_user: dict = Depends(require_subscription()),
):
    await verify_child_ownership(child_profile_id, current_user)

    result = supabase.table("chat_sessions").select("*").eq(
        "id", session_id
    ).eq("child_profile_id", child_profile_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    return result.data[0]
