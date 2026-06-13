import os
import logging
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

TIER_LIMITS = {
    "trial": 100,
    "individual": 400,
    "premium": 1000,
    "classroom": 200,
}


def get_message_limit(subscription_status: str, subscription_plan: str | None) -> int:
    if subscription_status == "trial":
        return TIER_LIMITS["trial"]
    plan = (subscription_plan or "individual").lower()
    return TIER_LIMITS.get(plan, 400)


def check_and_increment_message_count(
    child_profile_id: str,
    user_id: str,
    client_id: str,
    limit: int,
) -> dict:
    """
    Check message count for a child and increment if under limit.
    Returns {"allowed": bool, "current": int, "limit": int}
    Row is created automatically on first message (upsert pattern).
    """
    result = supabase.table("message_counts").select("*").eq(
        "child_profile_id", child_profile_id
    ).execute()

    current = result.data[0]["total_messages"] if result.data else 0

    if current >= limit:
        return {"allowed": False, "current": current, "limit": limit}

    if result.data:
        supabase.table("message_counts").update({
            "total_messages": current + 1,
            "updated_at": "now()",
        }).eq("child_profile_id", child_profile_id).execute()
    else:
        supabase.table("message_counts").insert({
            "child_profile_id": child_profile_id,
            "user_id": user_id,
            "client_id": client_id,
            "total_messages": 1,
        }).execute()

    return {"allowed": True, "current": current + 1, "limit": limit}
