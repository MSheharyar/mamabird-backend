"""
White-label business-assistant DEMO (no auth).

Shows prospects (e.g. a PPC agency and their clients) how the same engine that
powers the kid tutor can be re-skinned as an on-site AI assistant for ANY
business: it answers visitor questions from the business's own info and captures
leads. Two sample tenants ship here — a car-rental company and a pharmacy — but
every field below is exactly what would live in `client_configs` for a real
white-label client, so nothing here is hardcoded into business logic.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from app.services.sanitizer import sanitize_message, check_response_safety
from app.services.redis_client import incr_with_ttl
from app.services.claude_service import chat_business
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo/business", tags=["demo-business"])

# Per-IP rolling cap so the public demo can't run up an Anthropic bill.
_DEMO_MSG_LIMIT = 20
_DEMO_WINDOW_SECONDS = 3600  # 1 hour

# ── Sample white-label tenants ────────────────────────────────────────────────
# In production each of these is a row in `client_configs`. The knowledge base
# is the ONLY source of truth the assistant may answer from.
BUSINESSES = {
    "car_rental": {
        "name": "DriveEasy Car Rental",
        "tagline": "Great cars. Fair prices. On the road in minutes.",
        "industry": "car rental company",
        "theme": "#1e63d0",
        "accent": "#e8f0fd",
        "emoji": "🚗",
        "greeting": (
            "Hi! 👋 Welcome to DriveEasy Car Rental. I can help with our vehicles, "
            "prices, pickup locations and booking. What are you looking for?"
        ),
        "cta_goal": "reserving a vehicle or requesting a quote",
        "cta_label": "Get a quote",
        "lead_note": "DriveEasy will call you back to confirm your booking.",
        "guardrail": "",
        "suggested": [
            "What cars do you have?",
            "How much for an SUV for 3 days?",
            "What do I need to rent a car?",
            "Do you offer airport pickup?",
        ],
        "knowledge": """FLEET & DAILY RATES (before taxes):
- Economy (Toyota Corolla, 5 seats): $45/day
- Mid-size SUV (Toyota RAV4, 5 seats): $75/day
- Luxury (Mercedes E-Class): $140/day
- 7-seater Van (Kia Carnival): $95/day
Weekly rentals get the 7th day free.

WHAT YOU NEED TO RENT:
- Valid driver's license (held 1+ year)
- Minimum age 21 (25 for Luxury)
- A credit card in the renter's name for the security hold

INSURANCE & DEPOSIT:
- Basic liability insurance is included
- Full collision coverage: +$15/day
- Refundable security hold: $200 (released at return)

MILEAGE & FUEL:
- 200 free miles per day; $0.25 per extra mile
- Return with a full tank, or pay a $6/gallon refuel fee

LOCATIONS & HOURS:
- Downtown branch and Airport branch
- Open 7:00 AM – 10:00 PM, every day
- Airport pickup/drop-off: +$20 convenience fee

BOOKING & CANCELLATION:
- Reserve online, by phone, or through this chat (leave your details)
- Free cancellation up to 48 hours before pickup
- Under-24-hour cancellations are charged one day's rate""",
    },
    "pharmacy": {
        "name": "CarePlus Pharmacy",
        "tagline": "Your neighborhood pharmacy — faster refills, friendly care.",
        "industry": "community pharmacy",
        "theme": "#1f9d6b",
        "accent": "#e6f6ef",
        "emoji": "💊",
        "greeting": (
            "Hello! 👋 Welcome to CarePlus Pharmacy. I can help with hours, refills, "
            "transfers, vaccinations and delivery. How can I help you today?"
        ),
        "cta_goal": "starting a refill, transfer, or requesting a callback",
        "cta_label": "Request a callback",
        "lead_note": "A CarePlus pharmacist will call you back shortly.",
        "guardrail": (
            "IMPORTANT SAFETY RULE: You are NOT a medical professional. Never diagnose "
            "conditions, recommend or compare specific medications, or give dosage advice. "
            "If asked anything medical, say a CarePlus pharmacist will be happy to help and "
            "invite them to leave their details — and for any emergency, tell them to call 911."
        ),
        "suggested": [
            "What are your hours?",
            "Do you offer flu shots?",
            "Can I transfer my prescription?",
            "Do you deliver?",
        ],
        "knowledge": """HOURS:
- Monday–Saturday: 8:00 AM – 9:00 PM
- Sunday: 9:00 AM – 6:00 PM

PRESCRIPTIONS & REFILLS:
- Refill online, by phone, or through this chat — usually ready in about 30 minutes
- Transfer a prescription from another pharmacy: bring your bottle or give us the pharmacy's
  name and we'll handle the transfer for you
- Automatic refill reminders available by text

VACCINATIONS (walk-in, no appointment needed):
- Flu, COVID-19, shingles, and pneumonia
- Flu shot: $0 with most insurance, $25 without
- Most major insurance plans accepted

DELIVERY:
- Free local delivery on orders over $20
- Same-day delivery if ordered before 2:00 PM

OTHER SERVICES:
- Free pharmacist consultations
- Free blood-pressure checks
- Medication packaging (pill organizers) for regular medications

INSURANCE:
- We accept most major insurance plans — bring your card and we'll check coverage""",
    },
}


def _build_prompt(biz: dict) -> str:
    """Assemble the business-mode system prompt from a tenant config."""
    guardrail = f"\n\n{biz['guardrail']}" if biz["guardrail"] else ""
    return f"""You are the friendly virtual assistant for {biz['name']}, a {biz['industry']}.

Answer visitor questions using ONLY the BUSINESS INFO below. Be warm, concise
(2–4 short sentences), and genuinely helpful — like a great front-desk employee.

Rules:
- Never invent prices, policies, hours, or facts that aren't in the BUSINESS INFO.
- If something isn't covered, don't guess. Say you'll connect them with the team
  and invite them to leave their name and phone number for a quick callback.
- Gently guide interested visitors toward {biz['cta_goal']}.
- Keep it human and upbeat. Use the visitor's words. Don't dump the whole list
  unless they ask for everything.{guardrail}

BUSINESS INFO for {biz['name']}:
{biz['knowledge']}"""


class DemoTurn(BaseModel):
    role: str
    content: str


class BusinessChatRequest(BaseModel):
    message: str
    history: Optional[List[DemoTurn]] = []

    @field_validator("message")
    @classmethod
    def bounded(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("message must be 1–500 characters")
        return v


class LeadRequest(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_ok(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 80:
            raise ValueError("name required")
        return v


def _get_business(biz_key: str) -> dict:
    biz = BUSINESSES.get(biz_key)
    if not biz:
        raise HTTPException(status_code=404, detail="Unknown demo business")
    return biz


_PAGE_PATH = Path(__file__).resolve().parent.parent / "static" / "business_demo.html"


@router.get("/page", response_class=HTMLResponse)
async def demo_page():
    """The self-contained sales demo page (Car Rental / Pharmacy toggle).
    Served same-origin so its fetch()es to the demo API need no CORS."""
    try:
        return HTMLResponse(_PAGE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Demo page not found")


@router.get("")
async def list_businesses():
    """Public metadata so the demo page can render either brand + suggestions."""
    return {
        "businesses": {
            key: {
                "key": key,
                "name": b["name"],
                "tagline": b["tagline"],
                "theme": b["theme"],
                "accent": b["accent"],
                "emoji": b["emoji"],
                "greeting": b["greeting"],
                "cta_label": b["cta_label"],
                "suggested": b["suggested"],
            }
            for key, b in BUSINESSES.items()
        }
    }


@router.post("/{biz_key}/chat")
@limiter.limit("12/minute")
async def business_chat(biz_key: str, request: Request, req: BusinessChatRequest):
    biz = _get_business(biz_key)

    # Per-IP hourly cap
    client_ip = request.client.host if request.client else "unknown"
    count = incr_with_ttl(f"bizdemo:{biz_key}:{client_ip}", _DEMO_WINDOW_SECONDS)
    if count > _DEMO_MSG_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={"code": "DEMO_LIMIT_REACHED",
                    "message": "Demo message limit reached — please try again later."},
        )

    san = sanitize_message(req.message)
    if not san["safe"]:
        raise HTTPException(status_code=400, detail="Message contains disallowed content.")

    safe_history = []
    for h in (req.history or []):
        if h.role not in ("user", "assistant") or not h.content:
            continue
        h_san = sanitize_message(h.content)
        if h_san["safe"]:
            safe_history.append({"role": h.role, "content": h_san["sanitized"]})
    safe_history = safe_history[-10:]

    result = await chat_business(_build_prompt(biz), safe_history, san["sanitized"])

    response_text = result.get("response", "")
    safety = check_response_safety(response_text)
    if not safety["safe"]:
        logger.warning("Business demo post-gen safety triggered (%s)", safety.get("reason"))
        response_text = (
            f"I'd love to help with that — let me connect you with the {biz['name']} team. "
            "Leave your name and phone number and we'll call you right back."
        )

    return {
        "response": response_text,
        "fallback": result.get("fallback", False) or not safety["safe"],
        "remaining": max(0, _DEMO_MSG_LIMIT - count),
    }


@router.post("/{biz_key}/lead")
@limiter.limit("6/minute")
async def capture_lead(biz_key: str, request: Request, req: LeadRequest):
    """
    Capture a lead from the chat. In production this would push to the client's
    CRM / email / webhook; for the demo we log it and return a confirmation so
    the captured lead is visible on screen.
    """
    biz = _get_business(biz_key)
    if not (req.phone or req.email):
        raise HTTPException(status_code=400, detail="Please provide a phone number or email.")

    ref = f"LD-{uuid4().hex[:6].upper()}"
    logger.info(
        "DEMO LEAD [%s] %s | name=%s phone=%s email=%s note=%s",
        biz_key, ref, req.name, req.phone, req.email, (req.message or "")[:120],
    )
    return {
        "ref": ref,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Thanks {req.name.split()[0]}! {biz['lead_note']}",
        "business": biz["name"],
    }
