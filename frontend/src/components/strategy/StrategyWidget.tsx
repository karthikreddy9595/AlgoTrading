'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Play,
  Pause,
  Square,
  TrendingUp,
  TrendingDown,
  Activity,
  ExternalLink,
  Loader2,
} from 'lucide-react'
import { strategyApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'
import type { StrategySubscription } from '@/types/strategy'

interface StrategyWidgetProps {
  subscription: StrategySubscription
  onUpdate?: (subscription: StrategySubscription) => void
  compact?: boolean
}

export function StrategyWidget({ subscription, onUpdate, compact = false }: StrategyWidgetProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [currentStatus, setCurrentStatus] = useState(subscription.status)

  const handleAction = async (action: 'start' | 'stop' | 'pause' | 'resume') => {
    setIsLoading(true)
    try {
      const updated = await strategyApi.subscriptionAction(subscription.id, action)
      setCurrentStatus(updated.status)
      onUpdate?.(updated)
    } catch (err: any) {
      console.error(`Failed to ${action} strategy:`, err)
      alert(err.response?.data?.detail || `Failed to ${action} strategy`)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
      case 'paused':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200'
      case 'stopped':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
    }
  }

  const PnLIndicator = ({ value, label }: { value: number; label: string }) => (
    <div className="text-center">
      <div className={cn(
        'text-lg font-semibold flex items-center justify-center gap-1',
        value >= 0 ? 'text-green-600' : 'text-red-600'
      )}>
        {value >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
        {formatCurrency(value)}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  )

  if (compact) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <Activity className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span className="font-medium truncate">
              {subscription.strategy?.name || 'Strategy'}
            </span>
            <span className={cn('px-1.5 py-0.5 rounded text-xs font-medium', getStatusColor(currentStatus))}>
              {currentStatus}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn(
              'text-sm font-medium',
              subscription.today_pnl >= 0 ? 'text-green-600' : 'text-red-600'
            )}>
              {formatCurrency(subscription.today_pnl)}
            </span>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : currentStatus === 'active' ? (
              <button
                onClick={() => handleAction('pause')}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                title="Pause"
              >
                <Pause className="h-4 w-4" />
              </button>
            ) : currentStatus === 'paused' ? (
              <button
                onClick={() => handleAction('resume')}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                title="Resume"
              >
                <Play className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={() => handleAction('start')}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                title="Start"
              >
                <Play className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-blue-500" />
          <h3 className="font-semibold">{subscription.strategy?.name || 'Strategy'}</h3>
          {subscription.is_paper_trading && (
            <span className="px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded text-xs">
              Paper
            </span>
          )}
        </div>
        <span className={cn('px-2 py-1 rounded-full text-xs font-medium', getStatusColor(currentStatus))}>
          {currentStatus}
        </span>
      </div>

      {/* P&L Display */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <PnLIndicator value={subscription.today_pnl} label="Today" />
        <PnLIndicator value={subscription.current_pnl} label="Total" />
      </div>

      {/* Capital & Symbols */}
      <div className="text-sm text-gray-500 mb-4">
        <div className="flex justify-between mb-1">
          <span>Capital</span>
          <span className="text-gray-900 dark:text-gray-100">{formatCurrency(subscription.capital_allocated)}</span>
        </div>
        {subscription.selected_symbols && subscription.selected_symbols.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {subscription.selected_symbols.slice(0, 3).map(s => (
              <span key={s} className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                {s.split(':')[1] || s}
              </span>
            ))}
            {subscription.selected_symbols.length > 3 && (
              <span className="text-xs text-gray-400">+{subscription.selected_symbols.length - 3} more</span>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        {isLoading ? (
          <div className="flex-1 flex justify-center py-2">
            <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
          </div>
        ) : (
          <>
            {currentStatus === 'inactive' || currentStatus === 'stopped' ? (
              <button
                onClick={() => handleAction('start')}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
              >
                <Play className="h-4 w-4" />
                Start
              </button>
            ) : currentStatus === 'active' ? (
              <>
                <button
                  onClick={() => handleAction('pause')}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm"
                >
                  <Pause className="h-4 w-4" />
                  Pause
                </button>
                <button
                  onClick={() => handleAction('stop')}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              </>
            ) : currentStatus === 'paused' ? (
              <>
                <button
                  onClick={() => handleAction('resume')}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
                >
                  <Play className="h-4 w-4" />
                  Resume
                </button>
                <button
                  onClick={() => handleAction('stop')}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              </>
            ) : null}
          </>
        )}
      </div>

      {/* Monitor Link */}
      <Link
        href={`/dashboard/strategies/${subscription.strategy?.slug || subscription.strategy_id}/monitor`}
        className="flex items-center justify-center gap-1 mt-3 text-sm text-blue-600 hover:underline"
      >
        View Details
        <ExternalLink className="h-3 w-3" />
      </Link>
    </div>
  )
}

// Dashboard section for all strategies
interface StrategyDashboardSectionProps {
  subscriptions: StrategySubscription[]
  onUpdate?: (subscription: StrategySubscription) => void
}

export function StrategyDashboardSection({ subscriptions, onUpdate }: StrategyDashboardSectionProps) {
  if (subscriptions.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="text-center">
          <Activity className="h-10 w-10 text-gray-300 mx-auto mb-2" />
          <p className="text-gray-500">No active strategies</p>
          <Link
            href="/dashboard/strategies"
            className="text-blue-600 hover:underline text-sm mt-2 inline-block"
          >
            Browse Strategies
          </Link>
        </div>
      </div>
    )
  }

  const activeSubscriptions = subscriptions.filter(s => s.status === 'active' || s.status === 'paused')
  const inactiveSubscriptions = subscriptions.filter(s => s.status === 'inactive' || s.status === 'stopped')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Your Strategies</h2>
        <Link
          href="/dashboard/strategies"
          className="text-sm text-blue-600 hover:underline"
        >
          View All
        </Link>
      </div>

      {/* Active Strategies */}
      {activeSubscriptions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activeSubscriptions.map(sub => (
            <StrategyWidget
              key={sub.id}
              subscription={sub}
              onUpdate={onUpdate}
            />
          ))}
        </div>
      )}

      {/* Inactive Strategies (compact view) */}
      {inactiveSubscriptions.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-500">Inactive</h3>
          {inactiveSubscriptions.map(sub => (
            <StrategyWidget
              key={sub.id}
              subscription={sub}
              onUpdate={onUpdate}
              compact
            />
          ))}
        </div>
      )}
    </div>
  )
}
