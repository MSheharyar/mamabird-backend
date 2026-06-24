import re
import html
from typing import Optional

_MAX_MESSAGE_LEN = 500
_MAX_NAME_LEN = 50
_MAX_GRADE_LEN = 20

# Post-generation response safety — catches obvious model misbehaviour
_RESPONSE_BAD_PATTERNS = re.compile(
    r"""
    \b(fuck|shit|ass\b|bitch|cunt|dick\b|cock\b|pussy\b|bastard|damn\b|crap\b)  # profanity
    |\b(kill\s+yourself|suicide|self.harm|blow\s+up|bomb|shoot|weapon)           # violence / self-harm
    |\b(sex|porn|nude|naked|condom|penis|vagina|breast\b)                        # adult content
    |\b(your\s+password|credit\s+card|social\s+security|ssn|bank\s+account)     # credential fishing
    |<script|javascript:|on\w+\s*=|data:text/html                               # XSS attempt in response
    """,
    re.IGNORECASE | re.VERBOSE,
)

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior)\s+instructions?",
    r"forget\s+(you\s+are|that\s+you)",
    r"pretend\s+you\s+are",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+safety",
    r"disregard\s+(all|your|previous)",
    r"system\s+prompt",
    r"new\s+persona",
    r"act\s+as\s+(if\s+you\s+are|a\s+different)",
    r"you\s+are\s+now\s+(?!chirpy|mama)",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE,
)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NAME_RE = re.compile(r"[^a-zA-Z\s\-']")
_GRADE_RE = re.compile(r"[^a-zA-Z0-9\s]")


def sanitize_message(text: str) -> dict:
    """
    Sanitize a chat message.
    Returns {"safe": bool, "sanitized": str, "reason": str | None}
    """
    if not isinstance(text, str):
        return {"safe": False, "sanitized": "", "reason": "invalid_type"}

    if len(text) > _MAX_MESSAGE_LEN:
        return {
            "safe": False,
            "sanitized": "",
            "reason": f"message_too_long (max {_MAX_MESSAGE_LEN} chars)",
        }

    cleaned = _CONTROL_CHARS_RE.sub("", text)
    cleaned = " ".join(cleaned.split())

    if _INJECTION_RE.search(cleaned):
        return {"safe": False, "sanitized": "", "reason": "prompt_injection_detected"}

    sanitized = html.escape(cleaned)

    return {"safe": True, "sanitized": sanitized, "reason": None}


def check_response_safety(text: str) -> dict:
    """
    Post-generation safety check on Claude's response before it reaches the client.
    Returns {"safe": bool, "reason": str | None}
    """
    if not isinstance(text, str) or not text.strip():
        return {"safe": False, "reason": "empty_response"}
    if _RESPONSE_BAD_PATTERNS.search(text):
        return {"safe": False, "reason": "unsafe_content_in_response"}
    return {"safe": True, "reason": None}


def sanitize_name(name: str) -> str:
    """Sanitize a child's name — letters, spaces, hyphens, apostrophes only."""
    if not isinstance(name, str):
        return ""
    cleaned = _NAME_RE.sub("", name).strip()
    return cleaned[:_MAX_NAME_LEN]


def sanitize_grade(grade: str) -> str:
    """Sanitize a grade field — alphanumeric only."""
    if not isinstance(grade, str):
        return ""
    cleaned = _GRADE_RE.sub("", grade).strip()
    return cleaned[:_MAX_GRADE_LEN]
