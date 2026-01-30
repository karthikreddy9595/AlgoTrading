"""
Payment API endpoints for subscription management and Razorpay integration.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models import User
from app.services.payment_service import PaymentService, RazorpayService
from app.schemas import (
    SubscriptionPlanResponse,
    CreateCheckoutRequest,
    CreateCheckoutResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    UserSubscriptionResponse,
    CancelSubscriptionRequest,
    CancelSubscriptionResponse,
    PaymentTransactionResponse,
    PaymentHistoryResponse,
    ActivateFreeResponse,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    """
    List all available subscription plans.
    Public endpoint - no authentication required.
    """
    service = PaymentService(db)
    plans = await service.get_plans()
    return plans


@router.get("/subscription", response_model=UserSubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's subscription details.
    """
    service = PaymentService(db)
    subscription = await service.get_user_subscription(current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found. Please subscribe to a plan.",
        )

    plan = await service.get_plan_by_id(subscription.plan_id)

    return UserSubscriptionResponse(
        id=subscription.id,
        plan_id=subscription.plan_id,
        plan_name=plan.name if plan else "Unknown",
        plan_type=plan.plan_type if plan else "unknown",
        status=subscription.status,
        billing_cycle=subscription.billing_cycle,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        next_billing_date=subscription.next_billing_date,
        auto_renew=subscription.auto_renew or False,
        cancelled_at=subscription.cancelled_at,
        features=plan.features if plan else None,
        max_strategies=plan.max_strategies if plan else None,
        max_capital=plan.max_capital if plan else None,
    )


@router.post("/checkout", response_model=CreateCheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Razorpay order for subscription checkout.
    Returns the order details needed to initiate payment on frontend.
    """
    # Check if Razorpay is configured
    razorpay_service = RazorpayService()
    if not razorpay_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service is not configured. Please contact support.",
        )

    service = PaymentService(db)

    try:
        checkout_data = await service.create_checkout(
            user=current_user,
            plan_id=request.plan_id,
            billing_cycle=request.billing_cycle.value,
            idempotency_key=request.idempotency_key,
        )
        return CreateCheckoutResponse(**checkout_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify Razorpay payment and activate subscription.
    Called after successful payment on frontend.
    """
    service = PaymentService(db)

    try:
        result = await service.verify_payment(
            user=current_user,
            razorpay_order_id=request.razorpay_order_id,
            razorpay_payment_id=request.razorpay_payment_id,
            razorpay_signature=request.razorpay_signature,
        )

        subscription = result.get("subscription")
        plan = result.get("plan")

        return VerifyPaymentResponse(
            success=result["success"],
            message=result["message"],
            subscription=UserSubscriptionResponse(
                id=subscription.id,
                plan_id=subscription.plan_id,
                plan_name=plan.name if plan else "Unknown",
                plan_type=plan.plan_type if plan else "unknown",
                status=subscription.status,
                billing_cycle=subscription.billing_cycle,
                started_at=subscription.started_at,
                expires_at=subscription.expires_at,
                next_billing_date=subscription.next_billing_date,
                auto_renew=subscription.auto_renew or False,
                cancelled_at=subscription.cancelled_at,
                features=plan.features if plan else None,
                max_strategies=plan.max_strategies if plan else None,
                max_capital=plan.max_capital if plan else None,
            ) if subscription else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/activate-free", response_model=ActivateFreeResponse)
async def activate_free_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate the free (Starter) plan for the user.
    Use this when user signs up or wants to start with free tier.
    """
    service = PaymentService(db)

    try:
        result = await service.activate_free_plan(current_user)
        subscription = result.get("subscription")

        if subscription:
            plan = await service.get_plan_by_id(subscription.plan_id)
            return ActivateFreeResponse(
                success=result["success"],
                message=result["message"],
                subscription=UserSubscriptionResponse(
                    id=subscription.id,
                    plan_id=subscription.plan_id,
                    plan_name=plan.name if plan else "Starter",
                    plan_type=plan.plan_type if plan else "free",
                    status=subscription.status,
                    billing_cycle=subscription.billing_cycle,
                    started_at=subscription.started_at,
                    expires_at=subscription.expires_at,
                    next_billing_date=subscription.next_billing_date,
                    auto_renew=subscription.auto_renew or False,
                    cancelled_at=subscription.cancelled_at,
                    features=plan.features if plan else None,
                    max_strategies=plan.max_strategies if plan else None,
                    max_capital=plan.max_capital if plan else None,
                ),
            )
        return ActivateFreeResponse(
            success=result["success"],
            message=result["message"],
            subscription=None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/subscription/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel user's subscription.
    By default, cancels at end of billing period.
    Set cancel_immediately=true to cancel immediately.
    """
    service = PaymentService(db)

    try:
        result = await service.cancel_subscription(
            user=current_user,
            cancel_immediately=request.cancel_immediately,
            reason=request.reason,
        )
        return CancelSubscriptionResponse(
            success=result["success"],
            message=result["message"],
            effective_date=result.get("effective_date"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's payment transaction history.
    """
    service = PaymentService(db)
    result = await service.get_payment_history(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    # Enrich transactions with plan names
    transactions = []
    for txn in result["transactions"]:
        plan = await service.get_plan_by_id(txn.plan_id) if txn.plan_id else None
        transactions.append(PaymentTransactionResponse(
            id=txn.id,
            plan_id=txn.plan_id,
            plan_name=plan.name if plan else None,
            amount=txn.amount,
            currency=txn.currency,
            status=txn.status,
            payment_method=txn.payment_method,
            billing_cycle=txn.billing_cycle,
            billing_start=txn.billing_start,
            billing_end=txn.billing_end,
            description=txn.description,
            razorpay_payment_id=txn.razorpay_payment_id,
            created_at=txn.created_at,
        ))

    return PaymentHistoryResponse(
        transactions=transactions,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Razorpay webhook events.
    Verifies signature and processes events.
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify signature
    razorpay_service = RazorpayService()
    if not razorpay_service.verify_webhook_signature(body.decode(), signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event = payload.get("event", "")
    event_payload = payload.get("payload", {})

    service = PaymentService(db)
    result = await service.handle_webhook(event, event_payload)

    return {"status": "ok", **result}
