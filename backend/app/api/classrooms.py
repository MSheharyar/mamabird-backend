import re
import logging
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import require_role, get_tenant_db
from app.db.tenant import TenantSafeQuery
from app.services.sanitizer import sanitize_name, sanitize_grade, sanitize_message
from app.services.claude_service import generate_lesson_plan
from app.services.message_limit import get_message_limit
from app.services.pdf_service import generate_classroom_report
from app.config.client_config import get_client_config_by_id
from app.db.client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classrooms", tags=["classrooms"])

_MAX_STUDENTS_PER_TEACHER = 30
_CLASS_NAME_RE = re.compile(r"[^a-zA-Z0-9\s\-'.]")


def _clean_class_name(s: str) -> str:
    """Class names allow letters, digits, spaces, hyphens, apostrophes, dots."""
    return _CLASS_NAME_RE.sub("", s or "").strip()[:60]


# ─── Request models ─────────────────────────────────────────────────────────

class CreateClassroomRequest(BaseModel):
    name: str
    grade_level: Optional[str] = None


class UpdateClassroomRequest(BaseModel):
    name: Optional[str] = None
    grade_level: Optional[str] = None


class AddStudentRequest(BaseModel):
    child_name: str
    age: Optional[int] = None
    grade: Optional[str] = None


class AssignLessonRequest(BaseModel):
    subject: str
    grade: str
    duration: str
    focus_areas: Optional[str] = ""


# ─── Ownership helper ───────────────────────────────────────────────────────

def _owned_classroom(classroom_id: str, current_user: dict, db: TenantSafeQuery) -> dict:
    """Return the classroom row iff it belongs to this teacher + tenant, else 404."""
    res = db.table("classrooms").select("*").eq("id", classroom_id).execute()
    row = res.data[0] if res.data else None
    if not row or row.get("teacher_id") != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return row


def _class_students(classroom_id: str, db: TenantSafeQuery) -> list:
    return (db.table("child_profiles").select(
        "id, child_name, age, grade, classroom_id, created_at"
    ).eq("classroom_id", classroom_id).execute().data) or []


# ─── Classroom CRUD ─────────────────────────────────────────────────────────

@router.post("")
async def create_classroom(
    req: CreateClassroomRequest,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    name = _clean_class_name(req.name)
    if not name:
        raise HTTPException(status_code=400, detail="Invalid class name")
    grade = sanitize_grade(req.grade_level) if req.grade_level else None

    result = db.table("classrooms").insert({
        "teacher_id": current_user["user_id"],
        "name": name,
        "grade_level": grade,
    }).execute()
    return {"classroom": result.data[0]}


@router.get("")
async def list_classrooms(
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    classes = (db.table("classrooms").select("*").eq(
        "teacher_id", current_user["user_id"]
    ).order("created_at", desc=True).execute().data) or []

    # student counts per class (one query, grouped in Python)
    counts = defaultdict(int)
    profiles = (db.table("child_profiles").select("classroom_id").eq(
        "user_id", current_user["user_id"]
    ).execute().data) or []
    for p in profiles:
        if p.get("classroom_id"):
            counts[p["classroom_id"]] += 1

    for c in classes:
        c["student_count"] = counts.get(c["id"], 0)
    return {"classrooms": classes, "count": len(classes)}


@router.get("/{classroom_id}")
async def get_classroom(
    classroom_id: str,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    classroom = _owned_classroom(classroom_id, current_user, db)
    classroom["students"] = _class_students(classroom_id, db)
    return {"classroom": classroom}


@router.put("/{classroom_id}")
async def update_classroom(
    classroom_id: str,
    req: UpdateClassroomRequest,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    _owned_classroom(classroom_id, current_user, db)
    updates = {}
    if req.name is not None:
        name = _clean_class_name(req.name)
        if not name:
            raise HTTPException(status_code=400, detail="Invalid class name")
        updates["name"] = name
    if req.grade_level is not None:
        updates["grade_level"] = sanitize_grade(req.grade_level)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    result = db.table("classrooms").update(updates).eq("id", classroom_id).execute()
    return {"classroom": result.data[0] if result.data else None}


@router.delete("/{classroom_id}")
async def delete_classroom(
    classroom_id: str,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    _owned_classroom(classroom_id, current_user, db)
    # Unassign students (FK is ON DELETE SET NULL, but do it explicitly so the
    # response is correct even if the FK action isn't configured).
    db.table("child_profiles").update({"classroom_id": None}).eq(
        "classroom_id", classroom_id
    ).execute()
    db.table("classrooms").delete().eq("id", classroom_id).execute()
    return {"deleted": True}


# ─── Roster ─────────────────────────────────────────────────────────────────

@router.post("/{classroom_id}/students")
async def add_student(
    classroom_id: str,
    req: AddStudentRequest,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    _owned_classroom(classroom_id, current_user, db)

    clean_name = sanitize_name(req.child_name)
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid student name")
    clean_grade = sanitize_grade(req.grade) if req.grade else None

    # Global 30-students-per-teacher cap (consistent with profiles.py)
    existing = db.table("child_profiles").select("id").eq(
        "user_id", current_user["user_id"]
    ).execute()
    if len(existing.data or []) >= _MAX_STUDENTS_PER_TEACHER:
        raise HTTPException(
            status_code=400,
            detail=f"Teacher accounts support up to {_MAX_STUDENTS_PER_TEACHER} student profiles",
        )

    result = db.table("child_profiles").insert({
        "user_id": current_user["user_id"],
        "child_name": clean_name,
        "age": req.age,
        "grade": clean_grade,
        "classroom_id": classroom_id,
    }).execute()
    return {"student": result.data[0]}


@router.delete("/{classroom_id}/students/{profile_id}")
async def remove_student(
    classroom_id: str,
    profile_id: str,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    _owned_classroom(classroom_id, current_user, db)
    # Verify the student belongs to this teacher before touching it
    prof = db.table("child_profiles").select("id, user_id, classroom_id").eq(
        "id", profile_id
    ).execute()
    row = prof.data[0] if prof.data else None
    if not row or row.get("user_id") != current_user["user_id"] or row.get("classroom_id") != classroom_id:
        raise HTTPException(status_code=404, detail="Student not found in this class")

    # Remove from class (keeps the student's history)
    db.table("child_profiles").update({"classroom_id": None}).eq(
        "id", profile_id
    ).execute()
    return {"removed": True}


# ─── Class analytics ────────────────────────────────────────────────────────

def _build_analytics(classroom: dict, db: TenantSafeQuery) -> dict:
    students = _class_students(classroom["id"], db)
    ids = [s["id"] for s in students]

    per_student = []
    subject_totals = defaultdict(lambda: {"correct": 0, "total": 0})
    class_sessions = 0
    class_badges = 0

    if ids:
        progress = (db.table("progress").select(
            "child_profile_id, subject, score, total_questions"
        ).in_("child_profile_id", ids).execute().data) or []
        sessions = (db.table("chat_sessions").select(
            "child_profile_id, created_at"
        ).in_("child_profile_id", ids).execute().data) or []
        badges = (db.table("badges").select(
            "child_profile_id"
        ).in_("child_profile_id", ids).execute().data) or []
        msg_counts = (db.table("message_counts").select(
            "child_profile_id, total_messages"
        ).in_("child_profile_id", ids).execute().data) or []

        prog_by_child = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in progress:
            cid = r["child_profile_id"]
            prog_by_child[cid]["correct"] += r.get("score", 0)
            prog_by_child[cid]["total"] += r.get("total_questions", 1)
            subj = r.get("subject", "unknown")
            subject_totals[subj]["correct"] += r.get("score", 0)
            subject_totals[subj]["total"] += r.get("total_questions", 1)

        sess_by_child = defaultdict(int)
        last_active = {}
        for s in sessions:
            cid = s["child_profile_id"]
            sess_by_child[cid] += 1
            ts = s.get("created_at")
            if ts and (cid not in last_active or ts > last_active[cid]):
                last_active[cid] = ts

        badge_by_child = defaultdict(int)
        for b in badges:
            badge_by_child[b["child_profile_id"]] += 1

        msg_by_child = {m["child_profile_id"]: m.get("total_messages", 0) for m in msg_counts}

        class_sessions = sum(sess_by_child.values())
        class_badges = sum(badge_by_child.values())

        for s in students:
            cid = s["id"]
            p = prog_by_child[cid]
            acc = round(p["correct"] / p["total"] * 100, 1) if p["total"] else 0.0
            per_student.append({
                "id": cid,
                "child_name": s["child_name"],
                "grade": s.get("grade"),
                "sessions": sess_by_child.get(cid, 0),
                "questions": p["total"],
                "avg_score": acc,
                "badges": badge_by_child.get(cid, 0),
                "messages_used": msg_by_child.get(cid, 0),
                "last_active": last_active.get(cid),
            })

    subject_breakdown = {}
    for subj, v in subject_totals.items():
        acc = round(v["correct"] / v["total"] * 100, 1) if v["total"] else 0.0
        subject_breakdown[subj] = {"correct": v["correct"], "total": v["total"], "accuracy_pct": acc}

    total_correct = sum(v["correct"] for v in subject_totals.values())
    total_questions = sum(v["total"] for v in subject_totals.values())
    class_accuracy = round(total_correct / total_questions * 100, 1) if total_questions else 0.0

    return {
        "classroom": {"id": classroom["id"], "name": classroom["name"], "grade_level": classroom.get("grade_level")},
        "totals": {
            "students": len(students),
            "sessions": class_sessions,
            "questions": total_questions,
            "accuracy_pct": class_accuracy,
            "badges": class_badges,
        },
        "students": sorted(per_student, key=lambda x: x["child_name"].lower()),
        "subject_breakdown": subject_breakdown,
    }


@router.get("/{classroom_id}/analytics")
async def classroom_analytics(
    classroom_id: str,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    classroom = _owned_classroom(classroom_id, current_user, db)
    return _build_analytics(classroom, db)


# ─── Lesson plans (class-wide) ──────────────────────────────────────────────

@router.post("/{classroom_id}/assign-lesson")
async def assign_lesson(
    classroom_id: str,
    req: AssignLessonRequest,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    _owned_classroom(classroom_id, current_user, db)

    subject_san = sanitize_message(req.subject)
    if not subject_san["safe"]:
        raise HTTPException(status_code=400, detail={"code": "UNSAFE_INPUT", "message": "Invalid subject."})
    subject = subject_san["sanitized"]
    grade = sanitize_grade(req.grade)
    focus = sanitize_grade(req.focus_areas or "")

    config = get_client_config_by_id(db.client_id)
    plan = await generate_lesson_plan(
        config=config, subject=subject, grade=grade,
        duration=req.duration, focus_areas=focus,
    )
    if "error" in plan:
        raise HTTPException(status_code=503, detail=plan["error"])
    meta = plan.pop("_meta", {})

    title = f"{subject} - Grade {grade} - {req.duration}"
    saved = db.table("lesson_plans").insert({
        "user_id": current_user["user_id"],
        "classroom_id": classroom_id,
        "subject": subject,
        "grade": grade,
        "duration": req.duration,
        "focus_areas": focus,
        "plan_data": plan,
        "title": title,
    }).execute()

    db.table("usage_logs").insert({
        "user_id": current_user["user_id"],
        "endpoint": "/classrooms/assign-lesson",
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
        "cost_usd": float(meta.get("cost_usd", 0)),
        "model": "claude-sonnet-4-6",
        "duration_ms": 0,
        "was_fallback": False,
    }).execute()

    return {"lesson_plan_id": saved.data[0]["id"] if saved.data else None, "plan": plan}


@router.get("/{classroom_id}/lessons")
async def list_class_lessons(
    classroom_id: str,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    _owned_classroom(classroom_id, current_user, db)
    plans = (db.table("lesson_plans").select(
        "id, subject, grade, duration, title, plan_data, created_at"
    ).eq("classroom_id", classroom_id).order("created_at", desc=True).execute().data) or []
    return {"lesson_plans": plans}


# ─── Class report PDF ───────────────────────────────────────────────────────

@router.get("/{classroom_id}/report-pdf")
async def classroom_report_pdf(
    classroom_id: str,
    current_user: dict = Depends(require_role("teacher")),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    classroom = _owned_classroom(classroom_id, current_user, db)
    analytics = _build_analytics(classroom, db)

    config = get_client_config_by_id(db.client_id) if db.client_id else {}
    app_name = config.get("character_1_name", "MamaBird & Chirpy")
    app_domain = config.get("domain", "threebabybirdies.com")

    try:
        pdf_bytes = generate_classroom_report(analytics, app_name=app_name, app_domain=app_domain)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    safe_name = (classroom.get("name") or "class").replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="class_report_{safe_name}.pdf"'},
    )
