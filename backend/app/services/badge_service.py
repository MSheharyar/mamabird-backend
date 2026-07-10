import os
import logging
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

logger = logging.getLogger(__name__)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# Badge definitions — logic is code, display text is constant (not from client config)
BADGE_RULES = [
    {
        "badge_type": "first_session",
        "badge_name": "First Flight!",
        "badge_emoji": "🐣",
        "check": lambda s: s["total_sessions"] >= 1,
        "subject_specific": False,
    },
    {
        "badge_type": "perfect_score",
        "badge_name": "Perfect Score",
        "badge_emoji": "⭐",
        "check": lambda s: s["latest_score"] == s["latest_total"] and s["latest_total"] > 0,
        "subject_specific": False,
    },
    {
        "badge_type": "five_correct",
        "badge_name": "Flying High",
        "badge_emoji": "🦅",
        "check": lambda s: s["total_correct"] >= 5,
        "subject_specific": False,
    },
    {
        "badge_type": "ten_correct",
        "badge_name": "Sky Master",
        "badge_emoji": "🌟",
        "check": lambda s: s["total_correct"] >= 10,
        "subject_specific": False,
    },
    {
        "badge_type": "subject_master",
        "badge_name": "Subject Expert",
        "badge_emoji": "🎓",
        "check": lambda s: s["subject_correct"] >= 5,
        "subject_specific": True,
    },
    {
        "badge_type": "streak_3",
        "badge_name": "On a Roll!",
        "badge_emoji": "🔥",
        "check": lambda s: s["consecutive_correct"] >= 3,
        "subject_specific": False,
    },
]


def check_and_award_badges(
    child_profile_id: str,
    client_id: str,
    subject: str,
    progress_data: dict,
) -> list:
    """
    Check badge rules and award any newly earned badges.
    Returns list of newly awarded badge dicts.
    Idempotent — never double-awards.
    """
    try:
        # Fetch aggregate progress stats for this child
        all_progress = supabase.table("progress").select(
            "score, total_questions, subject"
        ).eq("child_profile_id", child_profile_id).execute()

        rows = all_progress.data or []
        total_sessions = len(rows)
        total_correct = sum(r.get("score", 0) for r in rows)
        subject_correct = sum(
            r.get("score", 0) for r in rows if r.get("subject") == subject
        )

        # Compute consecutive correct from recent progress (last 10 entries)
        recent = supabase.table("progress").select(
            "score, total_questions"
        ).eq("child_profile_id", child_profile_id).order(
            "session_date", desc=True
        ).limit(10).execute()
        consecutive_correct = 0
        for r in (recent.data or []):
            if r.get("score", 0) > 0 and r.get("total_questions", 1) > 0:
                if r["score"] >= r["total_questions"]:
                    consecutive_correct += 1
                else:
                    break
            else:
                break

        stats = {
            "total_sessions": total_sessions,
            "total_correct": total_correct,
            "subject_correct": subject_correct,
            "consecutive_correct": consecutive_correct,
            "latest_score": progress_data.get("score", 0),
            "latest_total": progress_data.get("total", 1),
        }

        # Fetch already-earned badge types for this child
        existing = supabase.table("badges").select("badge_type, subject").eq(
            "child_profile_id", child_profile_id
        ).execute()
        earned_types = set()
        for b in (existing.data or []):
            # subject is NULL for non-subject badges; normalise None -> "" so the
            # key matches the rule key below (otherwise badges re-award every turn).
            key = f"{b['badge_type']}:{b.get('subject') or ''}"
            earned_types.add(key)

        new_badges = []
        for rule in BADGE_RULES:
            badge_key = f"{rule['badge_type']}:{subject if rule['subject_specific'] else ''}"
            if badge_key in earned_types:
                continue
            if rule["check"](stats):
                insert_row = {
                    "child_profile_id": child_profile_id,
                    "client_id": client_id,
                    "badge_type": rule["badge_type"],
                    "badge_name": rule["badge_name"],
                    "badge_emoji": rule["badge_emoji"],
                    "subject": subject if rule["subject_specific"] else None,
                    "earned_at": "now()",
                }
                result = supabase.table("badges").insert(insert_row).execute()
                if result.data:
                    new_badges.append({
                        "badge_type": rule["badge_type"],
                        "badge_name": rule["badge_name"],
                        "badge_emoji": rule["badge_emoji"],
                        "subject": subject if rule["subject_specific"] else None,
                    })
                    logger.info("Badge awarded: %s to child %s", rule["badge_type"], child_profile_id)

        return new_badges

    except Exception as e:
        logger.error("Badge check failed: %s", e)
        return []
