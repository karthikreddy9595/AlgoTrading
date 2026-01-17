'use client'

import { useState, useEffect } from 'react'
import { X, DollarSign, Shield, TrendingUp, AlertCircle } from 'lucide-react'
import { backtestApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'

interface SubscribeModalProps {
  backtestId: string
  strategyName: string
  symbol: string
  minCapital: number
  onClose: () => void
  onSuccess: (subscriptionId: string) => void
  hasOptimization: boolean
}

export function SubscribeModal({
  backtestId,
  strategyName,
  symbol,
  minCapital,
  onClose,
  onSuccess,
  hasOptimization,
}: SubscribeModalProps) {
  const [capitalAllocated, setCapitalAllocated] = useState(minCapital)
  const [isPaperTrading, setIsPaperTrading] = useState(true)
  const [maxDrawdownPercent, setMaxDrawdownPercent] = useState(10)
  const [perTradeStopLossPercent, setPerTradeStopLossPercent] = useState(2)
  const [maxPositions, setMaxPositions] = useState(5)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      const response = await backtestApi.subscribeFromBacktest(backtestId, {
        capital_allocated: capitalAllocated,
        is_paper_trading: isPaperTrading,
        max_drawdown_percent: maxDrawdownPercent,
        per_trade_stop_loss_percent: perTradeStopLossPercent,
        max_positions: maxPositions,
      })

      onSuccess(response.subscription_id)
    } catch (err: any) {
      console.error('Failed to create subscription:', err)
      setError(err.response?.data?.detail || 'Failed to create subscription')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <div>
            <h2 className="text-2xl font-bold">Go Live with Strategy</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {strategyName} on {symbol}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Optimization Banner */}
        {hasOptimization && (
          <div className="m-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <div className="flex items-start gap-3">
              <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
              <div>
                <h4 className="font-medium text-green-800 dark:text-green-200">
                  Optimized Parameters Detected
                </h4>
                <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                  This subscription will use the best parameters from your optimization run.
                </p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Capital Allocation */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Capital Allocated
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="number"
                value={capitalAllocated}
                onChange={(e) => setCapitalAllocated(Number(e.target.value))}
                min={minCapital}
                step={1000}
                required
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Minimum: {formatCurrency(minCapital)}
            </p>
          </div>

          {/* Trading Mode */}
          <div>
            <label className="block text-sm font-medium mb-2">Trading Mode</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setIsPaperTrading(true)}
                className={cn(
                  'p-4 rounded-lg border-2 transition-all text-left',
                  isPaperTrading
                    ? 'border-primary bg-primary/5'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                )}
              >
                <div className="font-medium">Paper Trading</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Practice without real money
                </div>
              </button>
              <button
                type="button"
                onClick={() => setIsPaperTrading(false)}
                className={cn(
                  'p-4 rounded-lg border-2 transition-all text-left',
                  !isPaperTrading
                    ? 'border-primary bg-primary/5'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                )}
              >
                <div className="font-medium">Live Trading</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Trade with real money
                </div>
              </button>
            </div>
          </div>

          {/* Risk Management */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <h3 className="font-medium">Risk Management</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Max Drawdown */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Max Drawdown (%)
                </label>
                <input
                  type="number"
                  value={maxDrawdownPercent}
                  onChange={(e) => setMaxDrawdownPercent(Number(e.target.value))}
                  min={1}
                  max={50}
                  step={1}
                  required
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Maximum portfolio loss allowed
                </p>
              </div>

              {/* Stop Loss */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Per Trade Stop Loss (%)
                </label>
                <input
                  type="number"
                  value={perTradeStopLossPercent}
                  onChange={(e) => setPerTradeStopLossPercent(Number(e.target.value))}
                  min={0.5}
                  max={10}
                  step={0.5}
                  required
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Stop loss per individual trade
                </p>
              </div>

              {/* Max Positions */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Max Positions
                </label>
                <input
                  type="number"
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(Number(e.target.value))}
                  min={1}
                  max={20}
                  step={1}
                  required
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Maximum concurrent positions
                </p>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
              <div>
                <h4 className="font-medium text-red-800 dark:text-red-200">Error</h4>
                <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? 'Creating...' : 'Subscribe & Go Live'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
