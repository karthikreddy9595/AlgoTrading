'use client'

import { useState, useCallback, useEffect } from 'react'
import { paymentApi } from '@/lib/api'
import type {
  BillingCycle,
  CreateCheckoutResponse,
  VerifyPaymentResponse,
  UserSubscription,
  RazorpayOptions,
  RazorpayResponse,
} from '@/types/payment'

const RAZORPAY_SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js'

interface UseRazorpayOptions {
  onSuccess?: (subscription: UserSubscription) => void
  onError?: (error: string) => void
  onCancel?: () => void
}

interface UseRazorpayReturn {
  isLoading: boolean
  isScriptLoaded: boolean
  error: string | null
  initiatePayment: (planId: string, billingCycle: BillingCycle) => Promise<void>
  activateFreePlan: () => Promise<UserSubscription | null>
}

export function useRazorpay(options: UseRazorpayOptions = {}): UseRazorpayReturn {
  const { onSuccess, onError, onCancel } = options
  const [isLoading, setIsLoading] = useState(false)
  const [isScriptLoaded, setIsScriptLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load Razorpay script
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (window.Razorpay) {
      setIsScriptLoaded(true)
      return
    }

    const script = document.createElement('script')
    script.src = RAZORPAY_SCRIPT_URL
    script.async = true
    script.onload = () => setIsScriptLoaded(true)
    script.onerror = () => {
      setError('Failed to load payment gateway')
      onError?.('Failed to load payment gateway')
    }
    document.body.appendChild(script)

    return () => {
      // Don't remove script on unmount - it should persist
    }
  }, [onError])

  const verifyPayment = useCallback(
    async (response: RazorpayResponse): Promise<VerifyPaymentResponse> => {
      const result = await paymentApi.verifyPayment({
        razorpay_order_id: response.razorpay_order_id,
        razorpay_payment_id: response.razorpay_payment_id,
        razorpay_signature: response.razorpay_signature,
      })
      return result
    },
    []
  )

  const initiatePayment = useCallback(
    async (planId: string, billingCycle: BillingCycle): Promise<void> => {
      if (!isScriptLoaded) {
        const errorMsg = 'Payment gateway not ready. Please try again.'
        setError(errorMsg)
        onError?.(errorMsg)
        return
      }

      setIsLoading(true)
      setError(null)

      try {
        // Create checkout order
        const checkoutData: CreateCheckoutResponse = await paymentApi.createCheckout({
          plan_id: planId,
          billing_cycle: billingCycle,
        })

        // Configure Razorpay options
        const razorpayOptions: RazorpayOptions = {
          key: checkoutData.key_id,
          amount: checkoutData.amount,
          currency: checkoutData.currency,
          name: 'ArthaQuant',
          description: checkoutData.description,
          order_id: checkoutData.razorpay_order_id,
          prefill: {
            name: checkoutData.prefill.name,
            email: checkoutData.prefill.email,
            contact: checkoutData.prefill.contact,
          },
          notes: checkoutData.notes,
          theme: {
            color: '#7c3aed', // Primary purple color
          },
          handler: async (response: RazorpayResponse) => {
            try {
              setIsLoading(true)
              const verifyResult = await verifyPayment(response)

              if (verifyResult.success && verifyResult.subscription) {
                onSuccess?.(verifyResult.subscription)
              } else {
                const errorMsg = verifyResult.message || 'Payment verification failed'
                setError(errorMsg)
                onError?.(errorMsg)
              }
            } catch (err) {
              const errorMsg = err instanceof Error ? err.message : 'Payment verification failed'
              setError(errorMsg)
              onError?.(errorMsg)
            } finally {
              setIsLoading(false)
            }
          },
          modal: {
            ondismiss: () => {
              setIsLoading(false)
              onCancel?.()
            },
          },
        }

        // Open Razorpay checkout
        const razorpay = new window.Razorpay(razorpayOptions)
        razorpay.open()
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to initiate payment'
        setError(errorMsg)
        onError?.(errorMsg)
        setIsLoading(false)
      }
    },
    [isScriptLoaded, verifyPayment, onSuccess, onError, onCancel]
  )

  const activateFreePlan = useCallback(async (): Promise<UserSubscription | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await paymentApi.activateFree()
      if (result.success && result.subscription) {
        onSuccess?.(result.subscription)
        return result.subscription
      } else {
        const errorMsg = result.message || 'Failed to activate free plan'
        setError(errorMsg)
        onError?.(errorMsg)
        return null
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to activate free plan'
      setError(errorMsg)
      onError?.(errorMsg)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [onSuccess, onError])

  return {
    isLoading,
    isScriptLoaded,
    error,
    initiatePayment,
    activateFreePlan,
  }
}
