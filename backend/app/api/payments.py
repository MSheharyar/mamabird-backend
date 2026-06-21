import os
import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.db.client import get_supabase

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

PRICE_IDS = {
    "individual": os.getenv("STRIPE_PRICE_ID_INDIVIDUAL"),
    "premium":    os.getenv("STRIPE_PRICE_ID_PREMIUM"),
    "classroom":  os.getenv("STRIPE_PRICE_ID_CLASSROOM"),
}

PLAN_TO_STATUS = {
    "individual": "active",
    "premium":    "active",
    "classroom":  "active",
}

router = APIRouter(prefix="/payments", tags=["payments"])


class CheckoutRequest(BaseModel):
    plan: str          # "individual" | "premium" | "classroom"
    success_url: str
    cancel_url: str


@router.post("/create-checkout-session")
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    plan = body.plan.lower()
    price_id = PRICE_IDS.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}")

    user_id = current_user["user_id"]
    email = current_user.get("email", "")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=email or None,
            metadata={"user_id": user_id, "plan": plan},
            success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=body.cancel_url,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.StripeError as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=502, detail="Payment service error. Please try again.")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except stripe.errors.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    logger.info("Stripe event received: %s", event_type)

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan    = session.get("metadata", {}).get("plan", "individual")
        stripe_customer_id    = session.get("customer")
        stripe_subscription_id = session.get("subscription")

        if user_id:
            get_supabase().table("users").update({
                "subscription_status":   "active",
                "subscription_plan":     plan,
                "stripe_customer_id":    stripe_customer_id,
                "stripe_subscription_id": stripe_subscription_id,
            }).eq("id", user_id).execute()
            logger.info("User %s upgraded to plan=%s", user_id, plan)

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        stripe_subscription_id = sub.get("id")

        if stripe_subscription_id:
            get_supabase().table("users").update({
                "subscription_status": "cancelled",
            }).eq("stripe_subscription_id", stripe_subscription_id).execute()
            logger.info("Subscription cancelled: %s", stripe_subscription_id)

    elif event_type in ("invoice.payment_failed", "invoice.payment_action_required"):
        sub_id = event["data"]["object"].get("subscription")
        if sub_id:
            get_supabase().table("users").update({
                "subscription_status": "past_due",
            }).eq("stripe_subscription_id", sub_id).execute()
            logger.info("Payment failed for subscription: %s", sub_id)

    return JSONResponse({"received": True})


@router.get("/plans")
async def get_plans():
    """Return available plans and prices for the frontend."""
    return {
        "plans": [
            {
                "id": "individual",
                "name": "Individual Plan",
                "price_usd": 9.99,
                "messages_per_month": 400,
                "description": "Perfect for one child at home",
            },
            {
                "id": "premium",
                "name": "Premium Plan",
                "price_usd": 19.99,
                "messages_per_month": 1000,
                "description": "Multiple children, unlimited learning",
            },
            {
                "id": "classroom",
                "name": "Classroom Plan",
                "price_usd": 29.99,
                "messages_per_month": 200,
                "description": "For teachers and classroom use",
            },
        ]
    }
