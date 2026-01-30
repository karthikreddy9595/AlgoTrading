'use client'

import { useState, useEffect } from 'react'
import { Metadata } from 'next'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Check, X, Zap, Shield, TrendingUp, HeadphonesIcon,
  ArrowRight, HelpCircle, Sparkles
} from 'lucide-react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'
import { paymentApi } from '@/lib/api'
import { useRazorpay } from '@/hooks/useRazorpay'
import type { SubscriptionPlan, BillingCycle, PricingTier } from '@/types/payment'

// Static pricing tiers for display (enriched from API data)
const PRICING_TIERS: PricingTier[] = [
  {
    id: 'starter',
    name: 'Starter',
    subtitle: 'For Beginners',
    monthlyPrice: null,
    yearlyPrice: null,
    performanceFee: null,
    features: [
      'Paper trading only',
      '1 strategy subscription',
      'Up to 50K virtual capital',
      'Basic performance reports',
      'Email support',
    ],
    limitations: [
      'No live trading',
      'Limited strategy access',
    ],
    highlighted: false,
    ctaText: 'Start Free',
    planType: 'free',
  },
  {
    id: 'trader',
    name: 'Trader',
    subtitle: 'For Active Traders',
    monthlyPrice: 499,
    yearlyPrice: 4999,
    performanceFee: null,
    features: [
      'Live trading enabled',
      '3 strategy subscriptions',
      'Up to 5L capital',
      'Real-time notifications',
      'Email alerts',
      'Basic support',
    ],
    limitations: [],
    highlighted: false,
    ctaText: 'Subscribe Now',
    planType: 'subscription',
  },
  {
    id: 'professional',
    name: 'Professional',
    subtitle: 'Most Popular',
    monthlyPrice: 1499,
    yearlyPrice: 14999,
    performanceFee: null,
    features: [
      'Live trading enabled',
      '10 strategy subscriptions',
      'Up to 25L capital',
      'Real-time notifications',
      'SMS + Email alerts',
      'Priority support',
      'Advanced analytics',
    ],
    limitations: [],
    highlighted: true,
    ctaText: 'Subscribe Now',
    planType: 'subscription',
  },
  {
    id: 'elite',
    name: 'Elite',
    subtitle: 'Performance-Based',
    monthlyPrice: 999,
    yearlyPrice: 9999,
    performanceFee: 10,
    features: [
      'Unlimited strategies',
      'Unlimited capital',
      'Custom strategy development',
      'Dedicated account manager',
      '24/7 priority support',
      'API access',
      'White-glove onboarding',
    ],
    limitations: [],
    highlighted: false,
    ctaText: 'Contact Sales',
    planType: 'performance',
  },
]

const FAQ_ITEMS = [
  {
    question: 'What payment methods do you accept?',
    answer: 'We accept all major credit/debit cards, UPI, net banking, and popular wallets through Razorpay. All transactions are processed securely.',
  },
  {
    question: 'Can I switch plans later?',
    answer: 'Yes, you can upgrade or downgrade your plan at any time. When upgrading, you\'ll be charged the prorated difference. When downgrading, the new rate applies from your next billing cycle.',
  },
  {
    question: 'What happens when my subscription ends?',
    answer: 'Your active strategies will be paused, and you\'ll retain access to your data. You can reactivate by subscribing again, and your strategies will resume from where they left off.',
  },
  {
    question: 'Is there a free trial for paid plans?',
    answer: 'We offer a free Starter plan that lets you paper trade with one strategy. This allows you to experience the platform before committing to a paid plan.',
  },
  {
    question: 'How does the Elite performance fee work?',
    answer: 'The Elite plan charges a base fee plus 10% of your monthly profits. If you don\'t make a profit in a given month, you only pay the base fee. Profits are calculated at the end of each billing cycle.',
  },
  {
    question: 'Can I cancel my subscription?',
    answer: 'Yes, you can cancel anytime from your dashboard. Your subscription will remain active until the end of the current billing period. We don\'t offer refunds for partial periods.',
  },
]

export default function PricingPage() {
  const router = useRouter()
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('monthly')
  const [plans, setPlans] = useState<SubscriptionPlan[]>([])
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loadingPlanId, setLoadingPlanId] = useState<string | null>(null)
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null)

  const { initiatePayment, activateFreePlan, isLoading, error } = useRazorpay({
    onSuccess: (subscription) => {
      router.push('/dashboard?subscription=success')
    },
    onError: (error) => {
      console.error('Payment error:', error)
    },
    onCancel: () => {
      setLoadingPlanId(null)
    },
  })

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('access_token')
    setIsAuthenticated(!!token)

    // Fetch plans from API
    paymentApi.getPlans().then(setPlans).catch(console.error)
  }, [])

  const getPlanById = (tierName: string): SubscriptionPlan | undefined => {
    return plans.find(p => p.name.toLowerCase() === tierName.toLowerCase())
  }

  const handleSubscribe = async (tier: PricingTier) => {
    if (!isAuthenticated) {
      router.push(`/register?redirect=/pricing&plan=${tier.id}`)
      return
    }

    const plan = getPlanById(tier.name)
    if (!plan) {
      console.error('Plan not found:', tier.name)
      return
    }

    setLoadingPlanId(tier.id)

    if (tier.planType === 'free') {
      await activateFreePlan()
      setLoadingPlanId(null)
    } else if (tier.planType === 'performance') {
      // Elite plan - redirect to contact
      router.push('/contact?plan=elite')
    } else {
      await initiatePayment(plan.id, billingCycle)
      setLoadingPlanId(null)
    }
  }

  const getPrice = (tier: PricingTier): string => {
    if (tier.planType === 'free') return 'Free'
    const price = billingCycle === 'yearly' ? tier.yearlyPrice : tier.monthlyPrice
    if (!price) return 'Free'
    return `₹${price.toLocaleString('en-IN')}`
  }

  const getPeriod = (tier: PricingTier): string => {
    if (tier.planType === 'free') return 'forever'
    return billingCycle === 'yearly' ? '/year' : '/month'
  }

  const getSavings = (tier: PricingTier): number | null => {
    if (!tier.monthlyPrice || !tier.yearlyPrice) return null
    const monthlyCost = tier.monthlyPrice * 12
    const savings = ((monthlyCost - tier.yearlyPrice) / monthlyCost) * 100
    return Math.round(savings)
  }

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <Header />

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950 py-16 md:py-20">
        <div className="container mx-auto px-4 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <Sparkles className="h-4 w-4" />
            Simple, Transparent Pricing
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            Choose the Plan That Fits Your
            <span className="text-primary"> Trading Style</span>
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto mb-8">
            Start free with paper trading, or unlock live trading with our affordable plans.
            No hidden fees, cancel anytime.
          </p>

          {/* Billing Toggle */}
          <div className="inline-flex items-center gap-4 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-all ${
                billingCycle === 'monthly'
                  ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('yearly')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${
                billingCycle === 'yearly'
                  ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Yearly
              <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs rounded-full">
                Save 17%
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 -mt-8">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
            {PRICING_TIERS.map((tier) => {
              const savings = getSavings(tier)
              const isLoadingThis = loadingPlanId === tier.id

              return (
                <div
                  key={tier.id}
                  className={`relative rounded-2xl border ${
                    tier.highlighted
                      ? 'border-primary shadow-xl shadow-primary/10 scale-105'
                      : 'border-gray-200 dark:border-gray-800'
                  } bg-white dark:bg-gray-900 p-6 flex flex-col`}
                >
                  {tier.highlighted && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="px-4 py-1 bg-primary text-white text-sm font-medium rounded-full">
                        Most Popular
                      </span>
                    </div>
                  )}

                  <div className="mb-4">
                    <h3 className="text-xl font-bold">{tier.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{tier.subtitle}</p>
                  </div>

                  <div className="mb-6">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold">{getPrice(tier)}</span>
                      <span className="text-gray-500 dark:text-gray-400">{getPeriod(tier)}</span>
                    </div>
                    {tier.performanceFee && (
                      <p className="text-sm text-primary mt-1">
                        + {tier.performanceFee}% of profits
                      </p>
                    )}
                    {billingCycle === 'yearly' && savings && (
                      <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                        Save {savings}% vs monthly
                      </p>
                    )}
                  </div>

                  <ul className="space-y-3 mb-6 flex-grow">
                    {tier.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-3">
                        <Check className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{feature}</span>
                      </li>
                    ))}
                    {tier.limitations.map((limitation, idx) => (
                      <li key={`lim-${idx}`} className="flex items-start gap-3 opacity-60">
                        <X className="h-5 w-5 text-gray-400 flex-shrink-0 mt-0.5" />
                        <span className="text-sm text-gray-500 dark:text-gray-400">{limitation}</span>
                      </li>
                    ))}
                  </ul>

                  <button
                    onClick={() => handleSubscribe(tier)}
                    disabled={isLoadingThis || isLoading}
                    className={`w-full py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
                      tier.highlighted
                        ? 'bg-primary text-white hover:bg-primary/90'
                        : tier.planType === 'free'
                        ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white hover:bg-gray-200 dark:hover:bg-gray-700'
                        : 'border border-primary text-primary hover:bg-primary/5'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {isLoadingThis ? (
                      <>
                        <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        {tier.ctaText}
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </div>
              )
            })}
          </div>

          {error && (
            <div className="max-w-md mx-auto mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm text-center">
              {error}
            </div>
          )}
        </div>
      </section>

      {/* Feature Comparison */}
      <section className="py-16 bg-gray-50 dark:bg-gray-900/50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Compare Plans</h2>
            <p className="text-gray-600 dark:text-gray-400">
              See what's included in each plan
            </p>
          </div>

          <div className="max-w-5xl mx-auto overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-4 px-4 font-medium">Feature</th>
                  {PRICING_TIERS.map((tier) => (
                    <th key={tier.id} className="text-center py-4 px-4 font-medium">
                      {tier.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-sm">
                <ComparisonRow
                  feature="Live Trading"
                  values={[false, true, true, true]}
                />
                <ComparisonRow
                  feature="Paper Trading"
                  values={[true, true, true, true]}
                />
                <ComparisonRow
                  feature="Strategy Subscriptions"
                  values={['1', '3', '10', 'Unlimited']}
                />
                <ComparisonRow
                  feature="Max Capital"
                  values={['50K', '5L', '25L', 'Unlimited']}
                />
                <ComparisonRow
                  feature="Email Alerts"
                  values={[true, true, true, true]}
                />
                <ComparisonRow
                  feature="SMS Alerts"
                  values={[false, false, true, true]}
                />
                <ComparisonRow
                  feature="Priority Support"
                  values={[false, false, true, true]}
                />
                <ComparisonRow
                  feature="Custom Strategies"
                  values={[false, false, false, true]}
                />
                <ComparisonRow
                  feature="API Access"
                  values={[false, false, false, true]}
                />
                <ComparisonRow
                  feature="Dedicated Manager"
                  values={[false, false, false, true]}
                />
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Trust Indicators */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="text-center">
              <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="h-7 w-7 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Secure Payments</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                All payments are processed through Razorpay with bank-grade security.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="h-7 w-7 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Instant Activation</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Your subscription is activated immediately after payment.
              </p>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <HeadphonesIcon className="h-7 w-7 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Cancel Anytime</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                No lock-in contracts. Cancel your subscription at any time.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 bg-gray-50 dark:bg-gray-900/50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Frequently Asked Questions</h2>
            <p className="text-gray-600 dark:text-gray-400">
              Have questions? We've got answers.
            </p>
          </div>

          <div className="max-w-3xl mx-auto space-y-4">
            {FAQ_ITEMS.map((item, idx) => (
              <div
                key={idx}
                className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 overflow-hidden"
              >
                <button
                  onClick={() => setExpandedFaq(expandedFaq === idx ? null : idx)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <span className="font-medium pr-4">{item.question}</span>
                  <HelpCircle
                    className={`h-5 w-5 text-gray-400 flex-shrink-0 transition-transform ${
                      expandedFaq === idx ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                {expandedFaq === idx && (
                  <div className="px-4 pb-4 text-gray-600 dark:text-gray-400 text-sm">
                    {item.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Start Trading?</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-xl mx-auto">
            Join thousands of traders who use ArthaQuant to automate their trading.
            Start with our free plan - no credit card required.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary text-white rounded-lg hover:bg-primary/90 font-semibold"
            >
              Get Started Free <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/about"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 font-semibold"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}

function ComparisonRow({
  feature,
  values,
}: {
  feature: string
  values: (boolean | string)[]
}) {
  return (
    <tr className="border-b border-gray-200 dark:border-gray-800">
      <td className="py-4 px-4 text-gray-700 dark:text-gray-300">{feature}</td>
      {values.map((value, idx) => (
        <td key={idx} className="text-center py-4 px-4">
          {typeof value === 'boolean' ? (
            value ? (
              <Check className="h-5 w-5 text-green-500 mx-auto" />
            ) : (
              <X className="h-5 w-5 text-gray-300 dark:text-gray-600 mx-auto" />
            )
          ) : (
            <span className="text-gray-700 dark:text-gray-300 font-medium">{value}</span>
          )}
        </td>
      ))}
    </tr>
  )
}
