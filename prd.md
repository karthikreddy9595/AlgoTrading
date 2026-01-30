# Pricing Page with Razorpay Integration - PRD

## Overview
Implement a pricing page with Razorpay payment integration for the ArthaQuant AlgoTrading platform targeting Indian retail traders.

---

## Pricing Model

### Recommended Tiers

| Tier | Name | Monthly | Yearly | Key Limits |
|------|------|---------|--------|------------|
| Free | **Starter** | ₹0 | ₹0 | 1 strategy, ₹50K capital, Live trading |
| Basic | **Trader** | ₹499 | ₹4,999 | 3 strategies, ₹5L capital, Live trading |
| Pro | **Professional** | ₹1,499 | ₹14,999 | 10 strategies, ₹25L capital, Priority support |
| Elite | **Elite** | ₹999 + 5% profit | ₹9,999 + 5% profit | Unlimited, Custom strategies |

**Rationale**: Progressive limits on strategies and capital, yearly discount (~17%), performance-based option aligns platform success with trader success.

---

## Implementation

### Phase 1: Backend Setup

#### 1.1 Add Razorpay Configuration
**File**: `backend/app/core/config.py`
- Add `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` settings

**File**: `backend/.env`
- Add Razorpay credentials (test mode initially)

#### 1.2 Database Migration
**New File**: `backend/alembic/versions/006_add_payment_tables.py`
- Add to `user_subscriptions`: `razorpay_subscription_id`, `razorpay_customer_id`, `billing_cycle`, `auto_renew`, `cancelled_at`, `next_billing_date`
- Create `payment_transactions` table for payment audit trail

#### 1.3 Add Dependency
```bash
cd backend && uv add razorpay
```

### Phase 2: Backend Implementation

#### 2.1 Pydantic Schemas
**New File**: `backend/app/schemas/payment.py`
- `SubscriptionPlanResponse` - Plan details
- `CreateCheckoutRequest/Response` - Razorpay order creation
- `VerifyPaymentRequest/Response` - Payment verification
- `UserSubscriptionResponse` - User's subscription status
- `PaymentTransactionResponse` - Payment history

#### 2.2 Payment Service
**New File**: `backend/app/services/payment_service.py`
- `RazorpayService` - Low-level Razorpay SDK wrapper
- `PaymentService` - High-level subscription management:
  - `get_plans()` - List available plans
  - `create_checkout()` - Create Razorpay order
  - `verify_payment()` - Verify signature & activate subscription
  - `handle_webhook()` - Process Razorpay webhook events
  - `cancel_subscription()` - Cancel with end-of-period option

#### 2.3 API Endpoints
**New File**: `backend/app/api/v1/payments.py`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/payments/plans` | No | List all plans |
| GET | `/payments/subscription` | Yes | Get user's subscription |
| POST | `/payments/checkout` | Yes | Create Razorpay order |
| POST | `/payments/verify` | Yes | Verify payment & activate |
| POST | `/payments/subscription/cancel` | Yes | Cancel subscription |
| GET | `/payments/history` | Yes | Payment history |
| POST | `/payments/webhook/razorpay` | No* | Webhook handler |
| POST | `/payments/activate-free` | Yes | Activate free tier |

*Webhook uses signature verification instead of JWT

#### 2.4 Register Router
**File**: `backend/app/api/v1/router.py`
- Add `from app.api.v1 import payments`
- Add `api_router.include_router(payments.router)`

### Phase 3: Frontend Implementation

#### 3.1 Types & API Client
**New File**: `frontend/src/types/payment.ts`
- TypeScript interfaces for plans, subscriptions, Razorpay

**File**: `frontend/src/lib/api.ts`
- Add `paymentApi` object with all payment endpoints

#### 3.2 Razorpay Hook
**New File**: `frontend/src/hooks/useRazorpay.ts`
- Load Razorpay checkout script
- `initiatePayment(planId, billingCycle)` - Full payment flow
- Handle success/error/cancel callbacks

#### 3.3 Pricing Page
**New File**: `frontend/src/app/pricing/page.tsx`
- Hero section with billing toggle (monthly/yearly)
- 4 pricing cards matching tiers
- Feature comparison per plan
- Razorpay checkout integration
- FAQ section
- Responsive design matching existing purple/yellow theme

#### 3.4 Navigation Updates
**File**: `frontend/src/components/Header.tsx`
- Add "Pricing" link to navigation

**File**: `frontend/src/app/page.tsx`
- Add pricing CTA to landing page

### Phase 4: Database Seed

```sql
INSERT INTO subscription_plans (name, plan_type, price_monthly, price_yearly,
  performance_fee_percent, max_strategies, max_capital, features, is_active) VALUES
('Starter', 'free', NULL, NULL, NULL, 1, 50000,
  '{"live_trading": true}', true),
('Trader', 'subscription', 499, 4999, NULL, 3, 500000,
  '{"live_trading": true, "email_alerts": true}', true),
('Professional', 'subscription', 1499, 14999, NULL, 10, 2500000,
  '{"live_trading": true, "sms_alerts": true, "priority_support": true}', true),
('Elite', 'performance', 999, 9999, 5, NULL, NULL,
  '{"live_trading": true, "dedicated_support": true, "custom_strategies": true}', true);
```

---

## Files to Create/Modify

### New Files
| Path | Purpose |
|------|---------|
| `backend/alembic/versions/006_add_payment_tables.py` | DB migration |
| `backend/app/schemas/payment.py` | Pydantic schemas |
| `backend/app/services/payment_service.py` | Payment business logic |
| `backend/app/api/v1/payments.py` | REST endpoints |
| `frontend/src/types/payment.ts` | TypeScript types |
| `frontend/src/hooks/useRazorpay.ts` | Razorpay hook |
| `frontend/src/app/pricing/page.tsx` | Pricing page |

### Modified Files
| Path | Change |
|------|--------|
| `backend/app/core/config.py` | Add Razorpay settings |
| `backend/app/models/subscription.py` | Add PaymentTransaction model |
| `backend/app/api/v1/router.py` | Register payments router |
| `frontend/src/lib/api.ts` | Add payment API methods |
| `frontend/src/components/Header.tsx` | Add Pricing nav link |

---

## Security Considerations

1. **Webhook Signature Verification** - Always verify `X-Razorpay-Signature` header
2. **Idempotency Keys** - Prevent duplicate payments on retry
3. **HTTPS Only** - All payment endpoints must use HTTPS in production
4. **No Card Storage** - Razorpay handles PCI compliance
5. **Audit Trail** - Log all payment transactions in `payment_transactions` table

---

## Verification Plan

### Backend Testing
```bash
cd backend
uv run alembic upgrade head              # Apply migration
uv run pytest tests/test_api/test_payments.py  # Run payment tests
```

### Frontend Testing
```bash
cd frontend
npm run build                            # Verify no build errors
npm run dev                              # Manual testing
```

### End-to-End Testing
1. Navigate to `/pricing` page
2. Toggle billing cycle (monthly/yearly)
3. Click "Subscribe Now" on a paid plan
4. Complete Razorpay test payment
5. Verify redirect to dashboard with active subscription
6. Check subscription status in `/dashboard/settings`
7. Test webhook by triggering from Razorpay dashboard

### Razorpay Test Credentials
- Use Razorpay test mode keys
- Test card: `4111 1111 1111 1111`
- Any future expiry, any CVV
