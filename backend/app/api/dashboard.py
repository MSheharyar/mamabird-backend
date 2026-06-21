import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from supabase import create_client
from dotenv import load_dotenv

from app.api.auth import get_current_user
from app.api.dependencies import require_subscription, require_role, verify_child_ownership
from app.db.client import get_supabase
from app.services.message_limit import get_message_limit
from app.services.pdf_service import generate_progress_pdf
from app.config.client_config import get_client_config_by_id

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = get_supabase()

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(current_user: dict = Depends(require_subscription())):
    user_id = current_user["user_id"]

    # All child profiles for this user
    profiles = supabase.table("child_profiles").select(
        "id, child_name, client_id"
    ).eq("user_id", user_id).execute()
    profile_ids = [p["id"] for p in (profiles.data or [])]
    client_id = profiles.data[0]["client_id"] if profiles.data else None

    if not profile_ids:
        return {
            "total_sessions": 0,
            "total_messages": 0,
            "total_correct": 0,
            "accuracy_percent": 0.0,
            "subjects_practiced": [],
            "most_active_child": None,
            "recent_sessions": [],
            "usage_this_month": {"messages": 0, "cost_usd": 0.0},
        }

    # Session counts per child
    session_counts = defaultdict(int)
    all_sessions = supabase.table("chat_sessions").select(
        "id, child_profile_id, character, subject, created_at"
    ).in_("child_profile_id", profile_ids).order(
        "created_at", desc=True
    ).limit(100).execute()
    for s in (all_sessions.data or []):
        session_counts[s["child_profile_id"]] += 1
    total_sessions = sum(session_counts.values())

    # Progress totals
    progress = supabase.table("progress").select(
        "score, total_questions, subject, child_profile_id"
    ).in_("child_profile_id", profile_ids).execute()
    progress_rows = progress.data or []
    total_correct = sum(r.get("score", 0) for r in progress_rows)
    total_questions = sum(r.get("total_questions", 1) for r in progress_rows)
    total_messages = len(progress_rows)
    accuracy = round(total_correct / total_questions * 100, 1) if total_questions else 0.0
    subjects = list({r["subject"] for r in progress_rows if r.get("subject")})

    # Most active child
    most_active_id = max(session_counts, key=session_counts.get) if session_counts else None
    most_active_name = None
    if most_active_id:
        for p in (profiles.data or []):
            if p["id"] == most_active_id:
                most_active_name = p["child_name"]
                break

    # Recent sessions (last 5) with child name
    profile_name_map = {p["id"]: p["child_name"] for p in (profiles.data or [])}
    recent = []
    for s in (all_sessions.data or [])[:5]:
        recent.append({
            "id": s["id"],
            "child_name": profile_name_map.get(s["child_profile_id"], "Unknown"),
            "subject": s["subject"],
            "character": s["character"],
            "created_at": s["created_at"],
        })

    # Usage this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0).isoformat()
    usage = supabase.table("usage_logs").select(
        "input_tokens, output_tokens, cost_usd"
    ).eq("user_id", user_id).gte("created_at", month_start).execute()
    usage_rows = usage.data or []
    month_messages = len(usage_rows)
    month_cost = round(sum(float(r.get("cost_usd", 0)) for r in usage_rows), 4)

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_correct": total_correct,
        "accuracy_percent": accuracy,
        "subjects_practiced": subjects,
        "most_active_child": most_active_name,
        "recent_sessions": recent,
        "usage_this_month": {"messages": month_messages, "cost_usd": month_cost},
    }


@router.get("/child/{child_profile_id}")
async def child_dashboard(
    child_profile_id: str,
    current_user: dict = Depends(require_subscription()),
):
    profile = await verify_child_ownership(child_profile_id, current_user)
    client_id = profile.get("client_id")

    # Progress by subject
    progress = supabase.table("progress").select(
        "score, total_questions, subject, session_date"
    ).eq("child_profile_id", child_profile_id).execute()
    progress_rows = progress.data or []

    by_subject = defaultdict(lambda: {"correct": 0, "total": 0})
    session_dates = set()
    for r in progress_rows:
        subj = r.get("subject", "unknown")
        by_subject[subj]["correct"] += r.get("score", 0)
        by_subject[subj]["total"] += r.get("total_questions", 1)
        if r.get("session_date"):
            session_dates.add(str(r["session_date"])[:10])

    progress_by_subject = {}
    for subj, vals in by_subject.items():
        acc = round(vals["correct"] / vals["total"] * 100, 1) if vals["total"] else 0.0
        progress_by_subject[subj] = {
            "correct": vals["correct"],
            "total": vals["total"],
            "accuracy_pct": acc,
        }

    # Total sessions
    sessions = supabase.table("chat_sessions").select(
        "id, character, subject, created_at"
    ).eq("child_profile_id", child_profile_id).order(
        "created_at", desc=True
    ).limit(10).execute()
    total_sessions = len(progress_rows)

    # Streak days (consecutive days with at least one session)
    sorted_dates = sorted(session_dates, reverse=True)
    streak = 0
    prev = None
    for d in sorted_dates:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        if prev is None or (prev - dt).days == 1:
            streak += 1
            prev = dt
        else:
            break

    # Badges
    badges = supabase.table("badges").select(
        "badge_type, badge_name, badge_emoji, subject, earned_at"
    ).eq("child_profile_id", child_profile_id).order("earned_at", desc=True).execute()

    # Message count usage
    msg_count_row = supabase.table("message_counts").select("total_messages").eq(
        "child_profile_id", child_profile_id
    ).execute()
    used = msg_count_row.data[0]["total_messages"] if msg_count_row.data else 0

    user_row = supabase.table("users").select(
        "subscription_status, subscription_plan"
    ).eq("id", current_user["user_id"]).execute()
    user_data = user_row.data[0] if user_row.data else {}
    msg_limit = get_message_limit(
        user_data.get("subscription_status", "trial"),
        user_data.get("subscription_plan"),
    )

    return {
        "child_name": profile.get("child_name"),
        "age": profile.get("age"),
        "grade": profile.get("grade"),
        "total_sessions": total_sessions,
        "progress_by_subject": progress_by_subject,
        "recent_sessions": sessions.data or [],
        "badges": badges.data or [],
        "session_dates": sorted(list(session_dates)),
        "streak_days": streak,
        "message_count": {"used": used, "limit": msg_limit},
    }


@router.get("/usage")
async def usage_report(current_user: dict = Depends(require_role("parent", "teacher"))):
    # Get client_id for this user
    user_row = supabase.table("users").select("client_id").eq(
        "id", current_user["user_id"]
    ).execute()
    if not user_row.data:
        raise HTTPException(status_code=500, detail="User record not found")
    client_id = user_row.data[0]["client_id"]

    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    logs = supabase.table("usage_logs").select(
        "input_tokens, output_tokens, cost_usd, created_at"
    ).eq("client_id", client_id).gte("created_at", since).execute()

    daily = defaultdict(lambda: {"messages": 0, "cost_usd": 0.0})
    total_cost = 0.0
    for row in (logs.data or []):
        day = str(row["created_at"])[:10]
        daily[day]["messages"] += 1
        daily[day]["cost_usd"] = round(daily[day]["cost_usd"] + float(row.get("cost_usd", 0)), 6)
        total_cost += float(row.get("cost_usd", 0))

    daily_list = sorted(
        [{"date": d, **v} for d, v in daily.items()],
        key=lambda x: x["date"],
    )

    return {
        "daily": daily_list,
        "totals": {"messages": len(logs.data or []), "cost_usd": round(total_cost, 4)},
    }


@router.get("/child/{child_profile_id}/export-pdf")
async def export_child_pdf(
    child_profile_id: str,
    current_user: dict = Depends(require_subscription()),
):
    profile = await verify_child_ownership(child_profile_id, current_user)

    progress = supabase.table("progress").select(
        "score, total_questions, subject"
    ).eq("child_profile_id", child_profile_id).execute()
    progress_rows = progress.data or []

    by_subject = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in progress_rows:
        subj = r.get("subject", "unknown")
        by_subject[subj]["correct"] += r.get("score", 0)
        by_subject[subj]["total"] += r.get("total_questions", 1)

    progress_by_subject = {}
    for subj, vals in by_subject.items():
        acc = round(vals["correct"] / vals["total"] * 100, 1) if vals["total"] else 0.0
        progress_by_subject[subj] = {
            "correct": vals["correct"],
            "total": vals["total"],
            "accuracy_pct": acc,
        }

    sessions = supabase.table("chat_sessions").select("id").eq(
        "child_profile_id", child_profile_id
    ).execute()
    total_sessions = len(sessions.data or [])

    badges = supabase.table("badges").select(
        "badge_type, badge_name, badge_emoji, subject, earned_at"
    ).eq("child_profile_id", child_profile_id).order("earned_at", desc=True).execute()

    child_data = {
        "child_name": profile.get("child_name"),
        "age": profile.get("age"),
        "grade": profile.get("grade"),
        "total_sessions": total_sessions,
        "streak_days": 0,
    }

    user_row = supabase.table("users").select("client_id").eq(
        "id", current_user["user_id"]
    ).execute()
    client_id = user_row.data[0]["client_id"] if user_row.data else None
    config = get_client_config_by_id(client_id) if client_id else {}
    app_name = config.get("character_1_name", "MamaBird & Chirpy")
    app_domain = config.get("domain", "threebabybirdies.com")

    try:
        pdf_bytes = generate_progress_pdf(
            child_data,
            progress_by_subject,
            badges.data or [],
            app_name=app_name,
            app_domain=app_domain,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    safe_name = (profile.get("child_name") or "child").replace(" ", "_")
    filename = f"progress_report_{safe_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
