from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from enum import Enum


class PlanType(str, Enum):
    FREE = "free"
    SUBSCRIPTION = "subscription"
    PERFORMANCE = "performance"


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


# --- Plan Schemas ---

class SubscriptionPlanResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    plan_type: str
    price_monthly: Optional[Decimal] = None
    price_yearly: Optional[Decimal] = None
    performance_fee_percent: Optional[Decimal] = None
    max_strategies: Optional[int] = None
    max_capital: Optional[Decimal] = None
    features: Optional[Dict[str, Any]] = None
    is_active: bool

    class Config:
        from_attributes = True


class PlanListResponse(BaseModel):
    plans: List[SubscriptionPlanResponse]


# --- Checkout Schemas ---

class CreateCheckoutRequest(BaseModel):
    plan_id: UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    idempotency_key: Optional[str] = None


class CreateCheckoutResponse(BaseModel):
    order_id: str
    razorpay_order_id: str
    amount: int  # Amount in paise
    currency: str
    key_id: str
    plan_name: str
    billing_cycle: str
    description: str
    prefill: Dict[str, str]
    notes: Dict[str, str]


# --- Verify Payment Schemas ---

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    subscription: Optional["UserSubscriptionResponse"] = None


# --- User Subscription Schemas ---

class UserSubscriptionResponse(BaseModel):
    id: UUID
    plan_id: UUID
    plan_name: str
    plan_type: str
    status: str
    billing_cycle: Optional[str] = None
    started_at: datetime
    expires_at: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    auto_renew: bool
    cancelled_at: Optional[datetime] = None
    features: Optional[Dict[str, Any]] = None
    max_strategies: Optional[int] = None
    max_capital: Optional[Decimal] = None

    class Config:
        from_attributes = True


class CancelSubscriptionRequest(BaseModel):
    cancel_immediately: bool = False
    reason: Optional[str] = None


class CancelSubscriptionResponse(BaseModel):
    success: bool
    message: str
    effective_date: Optional[datetime] = None


# --- Payment Transaction Schemas ---

class PaymentTransactionResponse(BaseModel):
    id: UUID
    plan_id: Optional[UUID] = None
    plan_name: Optional[str] = None
    amount: Decimal
    currency: str
    status: str
    payment_method: Optional[str] = None
    billing_cycle: Optional[str] = None
    billing_start: Optional[datetime] = None
    billing_end: Optional[datetime] = None
    description: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentHistoryResponse(BaseModel):
    transactions: List[PaymentTransactionResponse]
    total: int
    page: int
    page_size: int


# --- Webhook Schemas ---

class RazorpayWebhookPayload(BaseModel):
    event: str
    payload: Dict[str, Any]
    created_at: Optional[int] = None


# --- Free Tier Activation ---

class ActivateFreeRequest(BaseModel):
    pass  # No data needed, just an authenticated request


class ActivateFreeResponse(BaseModel):
    success: bool
    message: str
    subscription: Optional[UserSubscriptionResponse] = None


# Update forward references
VerifyPaymentResponse.model_rebuild()
ActivateFreeResponse.model_rebuild()
