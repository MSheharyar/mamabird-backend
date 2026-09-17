"""
The contact form.

Until now contact.html composed a mailto:, because there was nowhere to
post to. That works without a backend but it stores nothing, it needs the
visitor to have a mail client configured, and on a phone it often opens
nothing at all. This is the somewhere.

Public and unauthenticated, like /leads/subscribe, and resolved to a
client the same way, so a white-label deployment files its own enquiries.
Rate limited because anything public and unauthenticated that writes rows
will eventually be found by a bot; the honeypot field the form already
carries is checked here too.

Mail is best-effort. If SMTP is not configured the row is still stored and
the caller still gets a success, because losing the enquiry would be worse
than a delayed notification. Whoever sets SMTP should check the table for
anything that arrived in the meantime.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
import logging
import os
import smtplib
from email.message import EmailMessage

from app.limiter import limiter
from app.db.client import get_supabase
from app.services.sanitizer import sanitize_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])

# The chips on the form. Anything else is somebody poking at the endpoint.
_TOPICS = {
    "Signed Copy", "School Visit", "Bulk Order",
    "Chirpy's Classroom", "Press", "Other",
}


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    topic: str = Field(default="Other", max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    # The form's hidden field. A real person leaves it empty.
    website: str | None = Field(default=None, max_length=200)


def _resolve_client_id(request: Request) -> str | None:
    """Same resolution auth.signup and leads.subscribe use."""
    domain = request.headers.get(
        "X-Client-Domain",
        os.getenv("DEFAULT_CLIENT_DOMAIN", "threebabybirdies.com"),
    )
    result = get_supabase().table("clients").select("id").eq(
        "domain", domain
    ).execute()
    return result.data[0]["id"] if result.data else None


def _notify(name: str, email: str, topic: str, message: str) -> None:
    """Best effort. A failure here must not lose the enquiry."""
    host = os.getenv("SMTP_HOST", "").strip()
    to = os.getenv("CONTACT_TO", os.getenv("SMTP_FROM", "")).strip()
    if not host or not to:
        logger.info("Contact: stored but not emailed, SMTP is not configured")
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = "[%s] %s" % (topic, name)
        msg["From"] = os.getenv("SMTP_FROM", to)
        msg["To"] = to
        # So a reply in the mail client goes to the visitor, not to us.
        msg["Reply-To"] = email
        msg.set_content(
            "From: %s <%s>\nTopic: %s\n\n%s\n" % (name, email, topic, message)
        )
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            user = os.getenv("SMTP_USER", "")
            if user:
                smtp.login(user, os.getenv("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
    except Exception:
        logger.exception("Contact: stored, but the notification did not send")


@router.post("")
@limiter.limit("4/minute")
async def submit(request: Request, req: ContactRequest):
    """Store an enquiry and try to email it on."""
    # The honeypot. Report success so a bot learns nothing from the reply.
    if req.website:
        logger.info("Contact: honeypot tripped, discarded")
        return {"message": "Thank you, your message is on its way."}

    client_id = _resolve_client_id(request)
    if not client_id:
        logger.error("Contact: no client row for the requested domain")
        raise HTTPException(status_code=500, detail="Client configuration not found")

    topic = req.topic if req.topic in _TOPICS else "Other"
    name = sanitize_name(req.name) or "Someone"

    try:
        get_supabase().table("contact_messages").insert({
            "client_id": client_id,
            "name": name,
            "email": str(req.email),
            "topic": topic,
            "message": req.message.strip(),
        }).execute()
    except Exception:
        logger.exception("Contact: could not store the enquiry")
        raise HTTPException(status_code=500, detail="Could not send your message")

    _notify(name, str(req.email), topic, req.message.strip())
    return {"message": "Thank you, your message is on its way."}
