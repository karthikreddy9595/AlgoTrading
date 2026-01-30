// Payment Types for AlgoTrading Platform

export type PlanType = 'free' | 'subscription' | 'performance'
export type BillingCycle = 'monthly' | 'yearly'
export type PaymentStatus = 'pending' | 'completed' | 'failed' | 'refunded'
export type SubscriptionStatus = 'active' | 'cancelled' | 'expired' | 'pending'

export interface SubscriptionPlan {
  id: string
  name: string
  description: string | null
  plan_type: PlanType
  price_monthly: number | null
  price_yearly: number | null
  performance_fee_percent: number | null
  max_strategies: number | null
  max_capital: number | null
  features: Record<string, boolean | string> | null
  is_active: boolean
}

export interface UserSubscription {
  id: string
  plan_id: string
  plan_name: string
  plan_type: PlanType
  status: SubscriptionStatus
  billing_cycle: BillingCycle | null
  started_at: string
  expires_at: string | null
  next_billing_date: string | null
  auto_renew: boolean
  cancelled_at: string | null
  features: Record<string, boolean | string> | null
  max_strategies: number | null
  max_capital: number | null
}

export interface CreateCheckoutRequest {
  plan_id: string
  billing_cycle: BillingCycle
  idempotency_key?: string
}

export interface CreateCheckoutResponse {
  order_id: string
  razorpay_order_id: string
  amount: number // in paise
  currency: string
  key_id: string
  plan_name: string
  billing_cycle: string
  description: string
  prefill: {
    name: string
    email: string
    contact: string
  }
  notes: {
    plan_id: string
    user_id: string
    billing_cycle: string
  }
}

export interface VerifyPaymentRequest {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

export interface VerifyPaymentResponse {
  success: boolean
  message: string
  subscription: UserSubscription | null
}

export interface CancelSubscriptionRequest {
  cancel_immediately?: boolean
  reason?: string
}

export interface CancelSubscriptionResponse {
  success: boolean
  message: string
  effective_date: string | null
}

export interface PaymentTransaction {
  id: string
  plan_id: string | null
  plan_name: string | null
  amount: number
  currency: string
  status: PaymentStatus
  payment_method: string | null
  billing_cycle: BillingCycle | null
  billing_start: string | null
  billing_end: string | null
  description: string | null
  razorpay_payment_id: string | null
  created_at: string
}

export interface PaymentHistoryResponse {
  transactions: PaymentTransaction[]
  total: number
  page: number
  page_size: number
}

export interface ActivateFreeResponse {
  success: boolean
  message: string
  subscription: UserSubscription | null
}

// Razorpay types
export interface RazorpayOptions {
  key: string
  amount: number
  currency: string
  name: string
  description: string
  order_id: string
  prefill: {
    name: string
    email: string
    contact: string
  }
  notes: Record<string, string>
  theme?: {
    color: string
  }
  handler: (response: RazorpayResponse) => void
  modal?: {
    ondismiss?: () => void
  }
}

export interface RazorpayResponse {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

export interface RazorpayInstance {
  open: () => void
  close: () => void
  on: (event: string, handler: () => void) => void
}

declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => RazorpayInstance
  }
}

// Pricing UI types
export interface PricingTier {
  id: string
  name: string
  subtitle: string
  monthlyPrice: number | null
  yearlyPrice: number | null
  performanceFee: number | null
  features: string[]
  limitations: string[]
  highlighted: boolean
  ctaText: string
  planType: PlanType
}
