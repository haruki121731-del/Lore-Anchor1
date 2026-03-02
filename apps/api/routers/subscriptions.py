"""
Stripe subscription management for Lore-Anchor.

Endpoints:
- POST /subscriptions/checkout: Create checkout session
- POST /subscriptions/portal: Create customer portal session
- POST /subscriptions/webhook: Handle Stripe webhooks
- GET /subscriptions/status: Get current user subscription status
"""

from __future__ import annotations

import logging
import os
from typing import Any

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from apps.api.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "")  # Monthly Pro plan
STRIPE_PRICE_ID_PRO_YEARLY = os.getenv("STRIPE_PRICE_ID_PRO_YEARLY", "")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Frontend URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://lore-anchor1-who4.vercel.app")


class CheckoutRequest(BaseModel):
    price_id: str | None = None  # If None, use default Pro plan
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


class SubscriptionStatusResponse(BaseModel):
    tier: str  # free, pro
    status: str  # active, canceled, past_due, etc.
    current_period_end: int | None = None  # Unix timestamp
    cancel_at_period_end: bool = False
    usage: dict[str, int] | None = None  # Monthly usage stats


def get_supabase_client():
    """Get Supabase client for database operations."""
    from supabase import create_client
    
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase not configured"
        )
    
    return create_client(supabase_url, supabase_key)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CheckoutResponse:
    """
    Create a Stripe Checkout session for subscription.
    
    The user will be redirected to Stripe's checkout page.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured"
        )
    
    user_id = user.get("id") or user.get("sub")
    user_email = user.get("email", "")
    
    # Use provided price ID or default to Pro monthly
    price_id = request.price_id or STRIPE_PRICE_ID_PRO
    
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No price ID configured"
        )
    
    try:
        # Create or retrieve Stripe customer
        supabase = get_supabase_client()
        
        # Check if user already has a Stripe customer ID
        profile_res = supabase.table("profiles").select("stripe_customer_id").eq("id", user_id).execute()
        
        stripe_customer_id = None
        if profile_res.data and profile_res.data[0].get("stripe_customer_id"):
            stripe_customer_id = profile_res.data[0]["stripe_customer_id"]
        
        if not stripe_customer_id:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=user_email,
                metadata={"supabase_user_id": user_id},
            )
            stripe_customer_id = customer.id
            
            # Save to profile
            supabase.table("profiles").update({
                "stripe_customer_id": stripe_customer_id
            }).eq("id", user_id).execute()
        
        # Create checkout session
        success_url = request.success_url or f"{FRONTEND_URL}/dashboard?checkout=success"
        cancel_url = request.cancel_url or f"{FRONTEND_URL}/pricing?checkout=cancel"
        
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                "metadata": {"supabase_user_id": user_id},
            },
            metadata={"supabase_user_id": user_id},
        )
        
        return CheckoutResponse(session_id=session.id, url=session.url)
        
    except stripe.error.StripeError as exc:
        logger.error(f"Stripe error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.post("/portal")
async def create_portal_session(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """
    Create a Stripe Customer Portal session.
    
    User can manage their subscription (cancel, update payment, etc.)
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured"
        )
    
    user_id = user.get("id") or user.get("sub")
    
    try:
        supabase = get_supabase_client()
        
        # Get Stripe customer ID
        profile_res = supabase.table("profiles").select("stripe_customer_id").eq("id", user_id).execute()
        
        if not profile_res.data or not profile_res.data[0].get("stripe_customer_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found"
            )
        
        stripe_customer_id = profile_res.data[0]["stripe_customer_id"]
        
        # Create portal session
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{FRONTEND_URL}/dashboard",
        )
        
        return {"url": session.url}
        
    except stripe.error.StripeError as exc:
        logger.error(f"Stripe error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> SubscriptionStatusResponse:
    """
    Get current user's subscription status.
    
    Returns tier (free/pro), status, and usage stats.
    """
    user_id = user.get("id") or user.get("sub")
    
    try:
        supabase = get_supabase_client()
        
        # Get profile with subscription info
        profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not profile_res.data:
            # Return free tier by default
            return SubscriptionStatusResponse(
                tier="free",
                status="active",
            )
        
        profile = profile_res.data[0]
        tier = profile.get("subscription_tier", "free")
        
        # Get monthly usage
        # Count images processed this month
        import datetime
        now = datetime.datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage_res = supabase.table("images") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .gte("created_at", start_of_month.isoformat()) \
            .execute()
        
        monthly_count = usage_res.count or 0
        
        # Free tier: 5 images/month
        # Pro tier: 100 images/month
        limit = 5 if tier == "free" else 100
        
        return SubscriptionStatusResponse(
            tier=tier,
            status=profile.get("subscription_status", "active"),
            current_period_end=profile.get("subscription_period_end"),
            cancel_at_period_end=profile.get("cancel_at_period_end", False),
            usage={
                "used": monthly_count,
                "limit": limit,
                "remaining": max(0, limit - monthly_count),
            }
        )
        
    except Exception as exc:
        logger.error(f"Error getting subscription status: {exc}")
        # Return free tier as fallback
        return SubscriptionStatusResponse(
            tier="free",
            status="active",
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
) -> dict[str, str]:
    """
    Handle Stripe webhook events.
    
    Events handled:
    - checkout.session.completed: Subscription created
    - invoice.paid: Subscription renewed
    - invoice.payment_failed: Payment failed
    - customer.subscription.deleted: Subscription canceled
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured"
        )
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid payload")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    
    logger.info(f"Stripe webhook received: {event['type']}")
    
    try:
        supabase = get_supabase_client()
        
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("supabase_user_id")
            
            if user_id:
                # Update user to Pro tier
                supabase.table("profiles").update({
                    "subscription_tier": "pro",
                    "subscription_status": "active",
                    "stripe_subscription_id": session.get("subscription"),
                }).eq("id", user_id).execute()
                
                logger.info(f"User {user_id} upgraded to Pro")
        
        elif event["type"] == "invoice.paid":
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            
            # Get subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id = subscription.get("metadata", {}).get("supabase_user_id")
            
            if user_id:
                supabase.table("profiles").update({
                    "subscription_status": "active",
                    "subscription_period_end": subscription.current_period_end,
                }).eq("id", user_id).execute()
                
                logger.info(f"Subscription renewed for user {user_id}")
        
        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            
            # Get subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id = subscription.get("metadata", {}).get("supabase_user_id")
            
            if user_id:
                supabase.table("profiles").update({
                    "subscription_status": "past_due",
                }).eq("id", user_id).execute()
                
                logger.warning(f"Payment failed for user {user_id}")
        
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            user_id = subscription.get("metadata", {}).get("supabase_user_id")
            
            if user_id:
                supabase.table("profiles").update({
                    "subscription_tier": "free",
                    "subscription_status": "canceled",
                    "stripe_subscription_id": None,
                }).eq("id", user_id).execute()
                
                logger.info(f"Subscription canceled for user {user_id}")
        
        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            user_id = subscription.get("metadata", {}).get("supabase_user_id")
            
            if user_id:
                supabase.table("profiles").update({
                    "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
                    "subscription_period_end": subscription.current_period_end,
                }).eq("id", user_id).execute()
        
    except Exception as exc:
        logger.error(f"Error processing webhook: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )
    
    return {"status": "ok"}
