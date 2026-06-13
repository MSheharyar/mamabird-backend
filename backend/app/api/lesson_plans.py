import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from supabase import create_client
from dotenv import load_dotenv

from app.api.auth import get_current_user
from app.api.dependencies import require_subscription
from app.services.sanitizer import sanitize_message, sanitize_grade
from app.services.claude_service import generate_lesson_plan
from app.config.client_config import get_client_config_by_id

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

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
):
    # Sanitize inputs
    subject_san = sanitize_message(req.subject)
    if not subject_san["safe"]:
        raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "message": "Invalid subject."})
    subject = subject_san["sanitized"]
    grade = sanitize_grade(req.grade)
    focus = sanitize_grade(req.focus_areas or "")

    # Get client_id for this user
    user_row = supabase.table("users").select("client_id").eq(
        "id", current_user["user_id"]
    ).execute()
    if not user_row.data:
        raise HTTPException(status_code=500, detail="User record not found")
    client_id = user_row.data[0]["client_id"]

    config = get_client_config_by_id(client_id)

    plan = await generate_lesson_plan(
        config=config,
        subject=subject,
        grade=grade,
        duration=req.duration,
        focus_areas=focus,
    )

    if "error" in plan:
        raise HTTPException(status_code=503, detail=plan["error"])

    # Extract and strip internal token metadata before saving
    meta = plan.pop("_meta", {})

    # Save to lesson_plans table
    title = f"{subject} - Grade {grade} - {req.duration}"
    insert_data = {
        "user_id": current_user["user_id"],
        "client_id": client_id,
        "subject": subject,
        "grade": grade,
        "duration": req.duration,
        "focus_areas": focus,
        "plan_data": plan,
        "title": title,
    }
    if req.child_profile_id:
        insert_data["child_profile_id"] = req.child_profile_id

    saved = supabase.table("lesson_plans").insert(insert_data).execute()
    lesson_plan_id = saved.data[0]["id"] if saved.data else None

    # Log usage
    supabase.table("usage_logs").insert({
        "client_id": client_id,
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
async def list_plans(current_user: dict = Depends(require_subscription())):
    plans = supabase.table("lesson_plans").select(
        "id, subject, grade, duration, title, created_at"
    ).eq("user_id", current_user["user_id"]).order(
        "created_at", desc=True
    ).execute()
    return {"lesson_plans": plans.data or []}


@router.get("/{plan_id}")
async def get_plan(plan_id: str, current_user: dict = Depends(require_subscription())):
    result = supabase.table("lesson_plans").select("*").eq("id", plan_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    plan = result.data[0]
    if plan["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    return plan
