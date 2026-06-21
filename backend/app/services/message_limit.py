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
    Atomically check and increment message count via a Postgres RPC.
    The DB function does the check + increment in one statement, eliminating
    the read-check-write race condition that existed in the old Python approach.
    Returns {"allowed": bool, "current": int, "limit": int}
    """
    result = supabase.rpc("increment_message_count", {
        "p_child_profile_id": child_profile_id,
        "p_user_id": user_id,
        "p_client_id": client_id,
        "p_limit": limit,
    }).execute()

    return result.data
