import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client
from dotenv import load_dotenv

from app.api.auth import get_current_user
from app.api.dependencies import verify_child_ownership

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("/{child_profile_id}")
async def get_badges(
    child_profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    await verify_child_ownership(child_profile_id, current_user)

    result = supabase.table("badges").select(
        "id, badge_type, badge_name, badge_emoji, subject, earned_at"
    ).eq("child_profile_id", child_profile_id).order(
        "earned_at", desc=True
    ).execute()

    return {"badges": result.data or []}
