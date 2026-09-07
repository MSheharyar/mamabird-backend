"""
Newsletter / lead capture.

Public (unauthenticated) endpoint used by the marketing site's newsletter
form. Client is resolved from the X-Client-Domain header exactly the way
auth.signup does it, so a white-label deployment captures leads against
its own client_id.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
import logging
import os

from app.limiter import limiter
from app.db.client import get_supabase
from app.db.tenant import TenantSafeQuery
from app.services.sanitizer import sanitize_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])

_ALLOWED_SOURCES = {
    "homepage_newsletter",
    "ebook_page",
    "footer",
    "quiz",
}


class SubscribeRequest(BaseModel):
    email: EmailStr
    first_name: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=40)


def _resolve_client_id(request: Request) -> str | None:
    """Same resolution auth.signup uses — header, else the default domain."""
    domain = request.headers.get(
        "X-Client-Domain",
        os.getenv("DEFAULT_CLIENT_DOMAIN", "threebabybirdies.com"),
    )
    result = get_supabase().table("clients").select("id").eq(
        "domain", domain
    ).execute()
    return result.data[0]["id"] if result.data else None


@router.post("/subscribe")
@limiter.limit("5/minute")
async def subscribe(request: Request, req: SubscribeRequest):
    """
    Store a newsletter signup. Re-subscribing with an address we already
    hold is a no-op that still reports success — the caller learns nothing
    about who is already on the list.
    """
    client_id = _resolve_client_id(request)
    if not client_id:
        logger.error("Lead subscribe: no client row for the requested domain")
        raise HTTPException(status_code=500, detail="Client configuration not found")

    db = TenantSafeQuery(get_supabase(), client_id)

    email = req.email.strip().lower()
    first_name = sanitize_name(req.first_name) if req.first_name else None
    source = req.source if req.source in _ALLOWED_SOURCES else "unknown"

    try:
        existing = db.table("leads").select("id").eq("email", email).execute()
        if existing.data:
            return {"status": "subscribed"}

        db.table("leads").insert({
            "email": email,
            "first_name": first_name or None,
            "source": source,
        }).execute()
    except Exception:
        # Never surface the driver error to a public endpoint.
        logger.exception("Lead subscribe failed for source=%s", source)
        raise HTTPException(
            status_code=500,
            detail="Could not save your subscription right now. Please try again.",
        )

    return {"status": "subscribed"}
