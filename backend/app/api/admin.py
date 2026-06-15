import os
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv

from app.api.dependencies import require_role

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_dep = Depends(require_role("admin"))


class ExtendTrialRequest(BaseModel):
    days: int


# ─── GET /admin/users ─────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(current_user: dict = Depends(require_role("admin"))):
    client_id = _get_admin_client_id(current_user["user_id"])

    users = supabase.table("users").select(
        "id, email, role, subscription_status, subscription_plan, trial_ends_at, created_at, client_id"
    ).eq("client_id", client_id).order("created_at", desc=True).execute()

    user_ids = [u["id"] for u in (users.data or [])]

    child_counts: dict[str, int] = defaultdict(int)
    if user_ids:
        profiles = supabase.table("child_profiles").select(
            "user_id"
        ).in_("user_id", user_ids).execute()
        for p in (profiles.data or []):
            child_counts[p["user_id"]] += 1

    result = []
    for u in (users.data or []):
        result.append({
            "id": u["id"],
            "email": u["email"],
            "role": u["role"],
            "subscription_status": u.get("subscription_status"),
            "subscription_plan": u.get("subscription_plan"),
            "trial_ends_at": u.get("trial_ends_at"),
            "child_count": child_counts[u["id"]],
            "created_at": u.get("created_at"),
        })

    return {"users": result, "total": len(result)}


# ─── GET /admin/users/{user_id} ───────────────────────────────────────────────

@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    client_id = _get_admin_client_id(current_user["user_id"])

    user_row = supabase.table("users").select("*").eq("id", user_id).eq(
        "client_id", client_id
    ).execute()
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_row.data[0]
    user.pop("password_hash", None)

    profiles = supabase.table("child_profiles").select("*").eq(
        "user_id", user_id
    ).execute()

    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    usage = supabase.table("usage_logs").select(
        "input_tokens, output_tokens, cost_usd, created_at"
    ).eq("user_id", user_id).gte("created_at", since).execute()

    total_cost = sum(float(r.get("cost_usd", 0)) for r in (usage.data or []))

    return {
        "user": user,
        "child_profiles": profiles.data or [],
        "usage_30d": {
            "messages": len(usage.data or []),
            "cost_usd": round(total_cost, 4),
        },
    }


# ─── PUT /admin/users/{user_id}/extend-trial ──────────────────────────────────

@router.put("/users/{user_id}/extend-trial")
async def extend_trial(
    user_id: str,
    req: ExtendTrialRequest,
    current_user: dict = Depends(require_role("admin")),
):
    if not (1 <= req.days <= 30):
        raise HTTPException(status_code=400, detail="days must be between 1 and 30")

    client_id = _get_admin_client_id(current_user["user_id"])

    user_row = supabase.table("users").select(
        "id, trial_ends_at, subscription_status"
    ).eq("id", user_id).eq("client_id", client_id).execute()

    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = user_row.data[0]
    current_trial_end = user.get("trial_ends_at")

    if current_trial_end:
        try:
            base = datetime.fromisoformat(current_trial_end.replace("Z", "+00:00"))
            if base < datetime.now(timezone.utc):
                base = datetime.now(timezone.utc)
        except (ValueError, TypeError):
            base = datetime.now(timezone.utc)
    else:
        base = datetime.now(timezone.utc)

    new_end = (base + timedelta(days=req.days)).isoformat()

    supabase.table("users").update({
        "trial_ends_at": new_end,
        "subscription_status": "trial",
    }).eq("id", user_id).execute()

    logger.info("Admin %s extended trial for user %s by %d days → %s",
                current_user["user_id"], user_id, req.days, new_end)

    return {"message": f"Trial extended by {req.days} days", "trial_ends_at": new_end}


# ─── PUT /admin/users/{user_id}/cancel ────────────────────────────────────────

@router.put("/users/{user_id}/cancel")
async def cancel_subscription(
    user_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    client_id = _get_admin_client_id(current_user["user_id"])

    user_row = supabase.table("users").select("id").eq("id", user_id).eq(
        "client_id", client_id
    ).execute()
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc).isoformat()
    supabase.table("users").update({
        "subscription_status": "cancelled",
        "subscription_ends_at": now,
    }).eq("id", user_id).execute()

    logger.info("Admin %s cancelled subscription for user %s", current_user["user_id"], user_id)

    return {"message": "Subscription cancelled", "subscription_ends_at": now}


# ─── GET /admin/stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(current_user: dict = Depends(require_role("admin"))):
    client_id = _get_admin_client_id(current_user["user_id"])

    users = supabase.table("users").select(
        "id, subscription_status"
    ).eq("client_id", client_id).execute()
    user_rows = users.data or []

    total_users = len(user_rows)
    active_subscribers = sum(1 for u in user_rows if u.get("subscription_status") == "active")
    trial_users = sum(1 for u in user_rows if u.get("subscription_status") == "trial")

    children = supabase.table("child_profiles").select(
        "id"
    ).eq("client_id", client_id).execute()
    total_children = len(children.data or [])

    sessions = supabase.table("chat_sessions").select(
        "id"
    ).eq("client_id", client_id).execute()
    total_sessions = len(sessions.data or [])

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0).isoformat()
    usage = supabase.table("usage_logs").select(
        "cost_usd"
    ).eq("client_id", client_id).gte("created_at", month_start).execute()
    api_cost_this_month = round(
        sum(float(r.get("cost_usd", 0)) for r in (usage.data or [])), 4
    )

    return {
        "total_users": total_users,
        "active_subscribers": active_subscribers,
        "trial_users": trial_users,
        "total_children": total_children,
        "total_sessions": total_sessions,
        "api_cost_this_month": api_cost_this_month,
    }


# ─── GET /admin/usage ─────────────────────────────────────────────────────────

@router.get("/usage")
async def admin_usage(current_user: dict = Depends(require_role("admin"))):
    client_id = _get_admin_client_id(current_user["user_id"])

    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    logs = supabase.table("usage_logs").select(
        "cost_usd, created_at"
    ).eq("client_id", client_id).gte("created_at", since).execute()

    daily: dict = defaultdict(lambda: {"messages": 0, "cost_usd": 0.0})
    for row in (logs.data or []):
        day = str(row["created_at"])[:10]
        daily[day]["messages"] += 1
        daily[day]["cost_usd"] = round(daily[day]["cost_usd"] + float(row.get("cost_usd", 0)), 6)

    daily_list = sorted(
        [{"date": d, **v} for d, v in daily.items()],
        key=lambda x: x["date"],
    )

    return {
        "daily": daily_list,
        "totals": {
            "messages": len(logs.data or []),
            "cost_usd": round(sum(float(r.get("cost_usd", 0)) for r in (logs.data or [])), 4),
        },
    }


# ─── Helper ───────────────────────────────────────────────────────────────────

def _get_admin_client_id(admin_user_id: str) -> str:
    row = supabase.table("users").select("client_id").eq("id", admin_user_id).execute()
    if not row.data or not row.data[0].get("client_id"):
        raise HTTPException(status_code=500, detail="Admin client_id not found")
    return row.data[0]["client_id"]
