import logging
from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.api.dependencies import get_tenant_db, verify_child_ownership
from app.db.tenant import TenantSafeQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("/{child_profile_id}")
async def get_badges(
    child_profile_id: str,
    current_user: dict = Depends(get_current_user),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    await verify_child_ownership(child_profile_id, current_user)

    result = db.table("badges").select(
        "id, badge_type, badge_name, badge_emoji, subject, earned_at"
    ).eq("child_profile_id", child_profile_id).order(
        "earned_at", desc=True
    ).execute()

    return {"badges": result.data or []}
