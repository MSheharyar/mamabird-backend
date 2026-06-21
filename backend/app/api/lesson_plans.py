import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.api.auth import get_current_user
from app.api.dependencies import require_subscription, get_tenant_db
from app.db.tenant import TenantSafeQuery
from app.services.sanitizer import sanitize_message, sanitize_grade
from app.services.claude_service import generate_lesson_plan
from app.config.client_config import get_client_config_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lesson-plans", tags=["lesson-plans"])


class LessonPlanRequest(BaseModel):
    subject: str
    grade: str
    duration: str
    focus_areas: Optional[str] = ""
    child_profile_id: Optional[str] = None


@router.post("/generate")
async def generate(
    req: LessonPlanRequest,
    current_user: dict = Depends(require_subscription()),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    subject_san = sanitize_message(req.subject)
    if not subject_san["safe"]:
        raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "message": "Invalid subject."})
    subject = subject_san["sanitized"]
    grade = sanitize_grade(req.grade)
    focus = sanitize_grade(req.focus_areas or "")

    config = get_client_config_by_id(db.client_id)

    plan = await generate_lesson_plan(
        config=config,
        subject=subject,
        grade=grade,
        duration=req.duration,
        focus_areas=focus,
    )

    if "error" in plan:
        raise HTTPException(status_code=503, detail=plan["error"])

    meta = plan.pop("_meta", {})

    title = f"{subject} - Grade {grade} - {req.duration}"
    insert_data = {
        "user_id": current_user["user_id"],
        "subject": subject,
        "grade": grade,
        "duration": req.duration,
        "focus_areas": focus,
        "plan_data": plan,
        "title": title,
    }
    if req.child_profile_id:
        insert_data["child_profile_id"] = req.child_profile_id

    saved = db.table("lesson_plans").insert(insert_data).execute()
    lesson_plan_id = saved.data[0]["id"] if saved.data else None

    db.table("usage_logs").insert({
        "user_id": current_user["user_id"],
        "endpoint": "/lesson-plans/generate",
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
        "cost_usd": float(meta.get("cost_usd", 0)),
        "model": "claude-sonnet-4-6",
        "duration_ms": 0,
        "was_fallback": False,
    }).execute()

    return {"lesson_plan_id": lesson_plan_id, "plan": plan}


@router.get("/")
async def list_plans(
    current_user: dict = Depends(require_subscription()),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    plans = db.table("lesson_plans").select(
        "id, subject, grade, duration, title, created_at"
    ).eq("user_id", current_user["user_id"]).order(
        "created_at", desc=True
    ).execute()
    return {"lesson_plans": plans.data or []}


@router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    current_user: dict = Depends(require_subscription()),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    result = db.table("lesson_plans").select("*").eq("id", plan_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    plan = result.data[0]
    if plan["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    return plan
