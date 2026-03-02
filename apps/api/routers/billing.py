"""Stripe billing router — checkout sessions, webhooks, and plan info."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apps.api.core.config import get_settings
from apps.api.core.security import get_current_user_id
from apps.api.services.database import DatabaseService, get_database_service

logger: logging.Logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ------------------------------------------------------------------
# GET /billing/plan — current user plan + usage
# ------------------------------------------------------------------
@router.get("/plan", summary="Get current plan and usage")
async def get_plan(
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> dict[str, Any]:
    """Return the user's current plan, monthly usage, and limit."""
    settings = get_settings()
    plan_row = db.get_user_plan(user_id)
    plan = plan_row["plan"] if plan_row else "free"
    usage = plan_row["monthly_upload_count"] if plan_row else 0
    limit = 0 if plan == "pro" else settings.FREE_MONTHLY_LIMIT
    return {
        "plan": plan,
        "monthly_upload_count": usage,
        "monthly_limit": limit,
        "unlimited": plan == "pro",
    }


# ------------------------------------------------------------------
# POST /billing/checkout — create Stripe Checkout session
# ------------------------------------------------------------------
@router.post("/checkout", summary="Create Stripe checkout session")
async def create_checkout(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: DatabaseService = Depends(get_database_service),
) -> dict[str, str]:
    """Create a Stripe Checkout Session for the Pro plan."""
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRO_PRICE_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Billing is not configured",
        )

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Get or create Stripe customer
    plan_row = db.get_user_plan(user_id)
    customer_id: str | None = plan_row["stripe_customer_id"] if plan_row else None

    if not customer_id:
        customer = stripe.Customer.create(metadata={"user_id": user_id})
        customer_id = customer.id
        db.upsert_user_plan(user_id, stripe_customer_id=customer_id)

    # Determine success/cancel URLs from Referer or use defaults
    origin = request.headers.get("origin", "http://localhost:3000")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.STRIPE_PRO_PRICE_ID, "quantity": 1}],
        success_url=f"{origin}/dashboard?checkout=success",
        cancel_url=f"{origin}/dashboard?checkout=cancel",
        metadata={"user_id": user_id},
    )

    return {"checkout_url": session.url or ""}


# ------------------------------------------------------------------
# POST /billing/webhook — Stripe webhook handler
# ------------------------------------------------------------------
@router.post("/webhook", summary="Stripe webhook handler")
async def stripe_webhook(request: Request) -> dict[str, str]:
    """Handle Stripe webhook events for subscription lifecycle."""
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Billing is not configured",
        )

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    db = get_database_service()

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        if customer_id:
            db.activate_pro_plan(customer_id, subscription_id)
            logger.info("Pro plan activated for customer %s", customer_id)

    elif event["type"] in (
        "customer.subscription.deleted",
        "customer.subscription.updated",
    ):
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")
        sub_status = subscription.get("status")
        if customer_id and sub_status in ("canceled", "unpaid", "past_due"):
            db.deactivate_pro_plan(customer_id)
            logger.info("Pro plan deactivated for customer %s", customer_id)

    return {"status": "ok"}
