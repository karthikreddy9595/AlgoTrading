"""
Payment service for handling Razorpay integration and subscription management.
"""

import razorpay
import hmac
import hashlib
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models import User, SubscriptionPlan, UserSubscription, PaymentTransaction


class RazorpayService:
    """Low-level wrapper for Razorpay SDK."""

    def __init__(self):
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        else:
            self.client = None

    def is_configured(self) -> bool:
        """Check if Razorpay is properly configured."""
        return self.client is not None

    def create_order(
        self,
        amount: int,  # Amount in paise
        currency: str = "INR",
        receipt: str = None,
        notes: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Create a Razorpay order."""
        if not self.is_configured():
            raise ValueError("Razorpay is not configured")

        order_data = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt or f"receipt_{uuid.uuid4().hex[:8]}",
        }
        if notes:
            order_data["notes"] = notes

        return self.client.order.create(data=order_data)

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify Razorpay payment signature."""
        if not self.is_configured():
            raise ValueError("Razorpay is not configured")

        try:
            self.client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
    ) -> bool:
        """Verify Razorpay webhook signature."""
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            return False

        expected_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """Fetch payment details from Razorpay."""
        if not self.is_configured():
            raise ValueError("Razorpay is not configured")
        return self.client.payment.fetch(payment_id)

    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[int] = None,
        notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Initiate a refund for a payment."""
        if not self.is_configured():
            raise ValueError("Razorpay is not configured")

        refund_data = {}
        if amount:
            refund_data["amount"] = amount
        if notes:
            refund_data["notes"] = notes

        return self.client.payment.refund(payment_id, refund_data)


class PaymentService:
    """High-level payment service for subscription management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.razorpay = RazorpayService()

    async def get_plans(self, include_inactive: bool = False) -> List[SubscriptionPlan]:
        """Get all available subscription plans."""
        query = select(SubscriptionPlan)
        if not include_inactive:
            query = query.where(SubscriptionPlan.is_active == True)
        query = query.order_by(SubscriptionPlan.price_monthly.nullsfirst())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_plan_by_id(self, plan_id: uuid.UUID) -> Optional[SubscriptionPlan]:
        """Get a specific plan by ID."""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_plan_by_name(self, name: str) -> Optional[SubscriptionPlan]:
        """Get a specific plan by name."""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.name == name)
        )
        return result.scalar_one_or_none()

    async def get_user_subscription(self, user_id: uuid.UUID) -> Optional[UserSubscription]:
        """Get user's current subscription."""
        result = await self.db.execute(
            select(UserSubscription).where(UserSubscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_checkout(
        self,
        user: User,
        plan_id: uuid.UUID,
        billing_cycle: str = "monthly",
        idempotency_key: str = None,
    ) -> Dict[str, Any]:
        """Create a Razorpay order for checkout."""
        # Get plan
        plan = await self.get_plan_by_id(plan_id)
        if not plan:
            raise ValueError("Plan not found")

        if plan.plan_type == "free":
            raise ValueError("Cannot checkout for a free plan. Use activate_free instead.")

        # Determine amount
        if billing_cycle == "yearly":
            amount = plan.price_yearly
        else:
            amount = plan.price_monthly
            billing_cycle = "monthly"

        if not amount:
            raise ValueError(f"Plan does not support {billing_cycle} billing")

        # Convert to paise (Razorpay requires amount in smallest currency unit)
        amount_paise = int(amount * 100)

        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"{user.id}_{plan_id}_{billing_cycle}_{uuid.uuid4().hex[:8]}"

        # Check for existing pending transaction with same idempotency key
        existing = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.idempotency_key == idempotency_key,
                PaymentTransaction.status == "pending"
            )
        )
        existing_txn = existing.scalar_one_or_none()
        if existing_txn and existing_txn.razorpay_order_id:
            # Return existing order
            return {
                "order_id": str(existing_txn.id),
                "razorpay_order_id": existing_txn.razorpay_order_id,
                "amount": amount_paise,
                "currency": "INR",
                "key_id": settings.RAZORPAY_KEY_ID,
                "plan_name": plan.name,
                "billing_cycle": billing_cycle,
                "description": f"{plan.name} - {billing_cycle.title()} Subscription",
                "prefill": {
                    "name": user.full_name,
                    "email": user.email,
                    "contact": user.phone or "",
                },
                "notes": {
                    "plan_id": str(plan_id),
                    "user_id": str(user.id),
                    "billing_cycle": billing_cycle,
                },
            }

        # Create Razorpay order
        razorpay_order = self.razorpay.create_order(
            amount=amount_paise,
            currency="INR",
            receipt=idempotency_key[:40],
            notes={
                "plan_id": str(plan_id),
                "user_id": str(user.id),
                "billing_cycle": billing_cycle,
            },
        )

        # Calculate billing period
        if billing_cycle == "yearly":
            billing_end = datetime.utcnow() + timedelta(days=365)
        else:
            billing_end = datetime.utcnow() + timedelta(days=30)

        # Create payment transaction record
        transaction = PaymentTransaction(
            user_id=user.id,
            plan_id=plan_id,
            razorpay_order_id=razorpay_order["id"],
            amount=amount,
            currency="INR",
            status="pending",
            billing_cycle=billing_cycle,
            billing_start=datetime.utcnow(),
            billing_end=billing_end,
            description=f"{plan.name} - {billing_cycle.title()} Subscription",
            idempotency_key=idempotency_key,
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)

        return {
            "order_id": str(transaction.id),
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "plan_name": plan.name,
            "billing_cycle": billing_cycle,
            "description": f"{plan.name} - {billing_cycle.title()} Subscription",
            "prefill": {
                "name": user.full_name,
                "email": user.email,
                "contact": user.phone or "",
            },
            "notes": {
                "plan_id": str(plan_id),
                "user_id": str(user.id),
                "billing_cycle": billing_cycle,
            },
        }

    async def verify_payment(
        self,
        user: User,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Dict[str, Any]:
        """Verify payment and activate subscription."""
        # Verify signature
        if not self.razorpay.verify_payment_signature(
            razorpay_order_id, razorpay_payment_id, razorpay_signature
        ):
            raise ValueError("Invalid payment signature")

        # Find transaction
        result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.razorpay_order_id == razorpay_order_id,
                PaymentTransaction.user_id == user.id,
            )
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise ValueError("Transaction not found")

        if transaction.status == "completed":
            # Already processed
            subscription = await self.get_user_subscription(user.id)
            return {
                "success": True,
                "message": "Payment already verified",
                "subscription": subscription,
            }

        # Fetch payment details from Razorpay
        payment_details = self.razorpay.fetch_payment(razorpay_payment_id)

        # Update transaction
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.razorpay_signature = razorpay_signature
        transaction.status = "completed"
        transaction.payment_method = payment_details.get("method")
        transaction.updated_at = datetime.utcnow()

        # Get or create user subscription
        subscription = await self.get_user_subscription(user.id)
        plan = await self.get_plan_by_id(transaction.plan_id)

        if subscription:
            # Update existing subscription
            subscription.plan_id = transaction.plan_id
            subscription.status = "active"
            subscription.payment_provider = "razorpay"
            subscription.payment_id = razorpay_payment_id
            subscription.billing_cycle = transaction.billing_cycle
            subscription.started_at = transaction.billing_start
            subscription.expires_at = transaction.billing_end
            subscription.next_billing_date = transaction.billing_end
            subscription.auto_renew = True
            subscription.cancelled_at = None
        else:
            # Create new subscription
            subscription = UserSubscription(
                user_id=user.id,
                plan_id=transaction.plan_id,
                status="active",
                payment_provider="razorpay",
                payment_id=razorpay_payment_id,
                billing_cycle=transaction.billing_cycle,
                started_at=transaction.billing_start,
                expires_at=transaction.billing_end,
                next_billing_date=transaction.billing_end,
                auto_renew=True,
            )
            self.db.add(subscription)

        # Link transaction to subscription
        await self.db.flush()
        transaction.user_subscription_id = subscription.id

        await self.db.commit()
        await self.db.refresh(subscription)

        return {
            "success": True,
            "message": "Payment verified and subscription activated",
            "subscription": subscription,
            "plan": plan,
        }

    async def activate_free_plan(self, user: User) -> Dict[str, Any]:
        """Activate the free (Starter) plan for a user."""
        # Get free plan
        free_plan = await self.get_plan_by_name("Starter")
        if not free_plan:
            raise ValueError("Free plan not found")

        # Check existing subscription
        existing = await self.get_user_subscription(user.id)
        if existing:
            if existing.plan.plan_type != "free":
                raise ValueError("User already has a paid subscription")
            # Already on free plan
            return {
                "success": True,
                "message": "Already on free plan",
                "subscription": existing,
            }

        # Create free subscription (no expiry)
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active",
            payment_provider=None,
            billing_cycle=None,
            started_at=datetime.utcnow(),
            expires_at=None,
            auto_renew=False,
        )
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        return {
            "success": True,
            "message": "Free plan activated",
            "subscription": subscription,
        }

    async def cancel_subscription(
        self,
        user: User,
        cancel_immediately: bool = False,
        reason: str = None,
    ) -> Dict[str, Any]:
        """Cancel user's subscription."""
        subscription = await self.get_user_subscription(user.id)
        if not subscription:
            raise ValueError("No active subscription found")

        plan = await self.get_plan_by_id(subscription.plan_id)
        if plan.plan_type == "free":
            raise ValueError("Cannot cancel free plan")

        now = datetime.utcnow()

        if cancel_immediately:
            subscription.status = "cancelled"
            subscription.cancelled_at = now
            subscription.auto_renew = False
            effective_date = now
        else:
            # Cancel at end of billing period
            subscription.auto_renew = False
            subscription.cancelled_at = now
            effective_date = subscription.expires_at

        await self.db.commit()

        return {
            "success": True,
            "message": "Subscription cancelled" if cancel_immediately else "Subscription will cancel at end of billing period",
            "effective_date": effective_date,
        }

    async def get_payment_history(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Get user's payment history."""
        offset = (page - 1) * page_size

        # Get total count
        count_result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.user_id == user_id,
                PaymentTransaction.status != "pending"
            )
        )
        total = len(count_result.scalars().all())

        # Get transactions
        result = await self.db.execute(
            select(PaymentTransaction)
            .where(
                PaymentTransaction.user_id == user_id,
                PaymentTransaction.status != "pending"
            )
            .order_by(PaymentTransaction.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        transactions = result.scalars().all()

        return {
            "transactions": transactions,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def handle_webhook(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Razorpay webhook events."""
        if event == "payment.captured":
            # Payment successful - handled by verify_payment
            return {"status": "acknowledged", "event": event}

        elif event == "payment.failed":
            # Update transaction status
            payment_entity = payload.get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")

            if order_id:
                result = await self.db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.razorpay_order_id == order_id
                    )
                )
                transaction = result.scalar_one_or_none()
                if transaction and transaction.status == "pending":
                    transaction.status = "failed"
                    transaction.error_message = payment_entity.get("error_description")
                    transaction.updated_at = datetime.utcnow()
                    await self.db.commit()

            return {"status": "processed", "event": event}

        elif event == "refund.created":
            # Mark transaction as refunded
            refund_entity = payload.get("refund", {}).get("entity", {})
            payment_id = refund_entity.get("payment_id")

            if payment_id:
                result = await self.db.execute(
                    select(PaymentTransaction).where(
                        PaymentTransaction.razorpay_payment_id == payment_id
                    )
                )
                transaction = result.scalar_one_or_none()
                if transaction:
                    transaction.status = "refunded"
                    transaction.updated_at = datetime.utcnow()
                    await self.db.commit()

            return {"status": "processed", "event": event}

        return {"status": "ignored", "event": event}


# Convenience functions

async def get_user_plan_limits(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Get user's plan limits for validation."""
    service = PaymentService(db)
    subscription = await service.get_user_subscription(user_id)

    if not subscription:
        # No subscription - use free plan limits
        free_plan = await service.get_plan_by_name("Starter")
        if free_plan:
            return {
                "max_strategies": free_plan.max_strategies or 1,
                "max_capital": float(free_plan.max_capital or 50000),
                "features": free_plan.features or {},
                "plan_type": "free",
            }
        return {
            "max_strategies": 1,
            "max_capital": 50000,
            "features": {},
            "plan_type": "free",
        }

    plan = await service.get_plan_by_id(subscription.plan_id)
    return {
        "max_strategies": plan.max_strategies,
        "max_capital": float(plan.max_capital) if plan.max_capital else None,
        "features": plan.features or {},
        "plan_type": plan.plan_type,
    }
