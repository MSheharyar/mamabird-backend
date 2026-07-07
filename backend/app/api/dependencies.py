from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from app.api.auth import get_current_user
from app.db.client import get_supabase
from app.db.tenant import TenantSafeQuery


def require_role(*allowed_roles: str):
    """FastAPI dependency factory — raises 403 if user role is not in allowed_roles."""
    def _check(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to: {', '.join(allowed_roles)}",
            )
        return current_user
    return _check


def require_subscription():
    """FastAPI dependency — raises 402 if user has no active subscription/trial."""
    def _check(current_user: dict = Depends(get_current_user)):
        result = get_supabase().table("users").select(
            "subscription_status, trial_ends_at"
        ).eq("id", current_user["user_id"]).execute()

        if not result.data:
            raise HTTPException(status_code=401, detail="User not found")

        user = result.data[0]
        status = user.get("subscription_status", "")
        trial_ends_at = user.get("trial_ends_at")

        if status in ("active",):
            return current_user

        if status == "trial":
            if trial_ends_at:
                try:
                    ends = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) <= ends:
                        return current_user
                except (ValueError, TypeError):
                    pass
            else:
                return current_user

        if status == "grace":
            return current_user

        raise HTTPException(
            status_code=402,
            detail={"code": "SUBSCRIPTION_REQUIRED", "message": "Active subscription required"},
        )
    return _check


async def get_tenant_db(current_user: dict = Depends(get_current_user)) -> TenantSafeQuery:
    """
    FastAPI dependency — client_id is embedded in the verified JWT payload,
    so no extra DB lookup is needed here.
    """
    client_id = current_user.get("client_id")
    if not client_id:
        raise HTTPException(status_code=500, detail="Client configuration not found")
    return TenantSafeQuery(get_supabase(), client_id)


async def verify_child_ownership(profile_id: str, current_user: dict) -> dict:
    """
    Verify that a child profile belongs to the requesting user.
    Raises 404 regardless of reason to avoid revealing existence.
    """
    result = get_supabase().table("child_profiles").select("*").eq(
        "id", profile_id
    ).eq("user_id", current_user["user_id"]).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return result.data[0]
