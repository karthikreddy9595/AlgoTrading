'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  Square,
  DollarSign,
  BarChart3,
  Clock,
  Loader2,
  Plus,
  Eye,
} from 'lucide-react'
import { strategyApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import type { StrategySubscription, Strategy } from '@/types/strategy'
import Link from 'next/link'
import { StrategyDetailsModal } from './components/StrategyDetailsModal'

interface SubscriptionWithStrategy extends StrategySubscription {
  strategy: Strategy
}

export default function LiveStrategiesPage() {
  const router = useRouter()
  const [subscriptions, setSubscriptions] = useState<SubscriptionWithStrategy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSubscription, setSelectedSubscription] = useState<SubscriptionWithStrategy | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  useEffect(() => {
    fetchSubscriptions()
  }, [])

  const fetchSubscriptions = async () => {
    try {
      setIsLoading(true)
      const subs = await strategyApi.getMySubscriptions()

      // Fetch strategy details for each subscription
      const subsWithStrategy = await Promise.all(
        subs.map(async (sub: StrategySubscription) => {
          try {
            const strategy = await strategyApi.get(sub.strategy_id)
            return { ...sub, strategy }
          } catch (err) {
            console.error(`Failed to fetch strategy ${sub.strategy_id}:`, err)
            return null
          }
        })
      )

      setSubscriptions(subsWithStrategy.filter((s): s is SubscriptionWithStrategy => s !== null))
    } catch (err: any) {
      console.error('Failed to fetch subscriptions:', err)
      setError(err.response?.data?.detail || 'Failed to load subscriptions')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAction = async (subscriptionId: string, action: 'start' | 'pause' | 'stop') => {
    try {
      await strategyApi.subscriptionAction(subscriptionId, action)
      // Refresh subscriptions
      await fetchSubscriptions()
    } catch (err: any) {
      console.error(`Failed to ${action} subscription:`, err)
      alert(`Failed to ${action} strategy: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleOpenDetails = (subscription: SubscriptionWithStrategy) => {
    setSelectedSubscription(subscription)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedSubscription(null)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <p className="text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={() => fetchSubscriptions()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const activeSubscriptions = subscriptions.filter((s) => s.status === 'active')
  const pausedSubscriptions = subscriptions.filter((s) => s.status === 'paused')
  const inactiveSubscriptions = subscriptions.filter((s) => s.status === 'inactive' || s.status === 'stopped')

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent">
            Live Strategies
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Monitor and control all your active trading strategies
          </p>
        </div>
        <Link
          href="/dashboard/strategies"
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all shadow-lg shadow-purple-500/25"
        >
          <Plus className="h-5 w-5" />
          Subscribe to Strategy
        </Link>
      </div>

      {subscriptions.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-12 text-center">
          <Activity className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">No Active Strategies</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Subscribe to a strategy to start automated trading
          </p>
          <Link
            href="/dashboard/strategies"
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all"
          >
            <Plus className="h-5 w-5" />
            Browse Strategies
          </Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Active Strategies */}
          {activeSubscriptions.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-green-600" />
                Active ({activeSubscriptions.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {activeSubscriptions.map((sub) => (
                  <StrategyCard
                    key={sub.id}
                    subscription={sub}
                    onAction={handleAction}
                    onOpenDetails={handleOpenDetails}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Paused Strategies */}
          {pausedSubscriptions.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Pause className="h-5 w-5 text-yellow-600" />
                Paused ({pausedSubscriptions.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {pausedSubscriptions.map((sub) => (
                  <StrategyCard
                    key={sub.id}
                    subscription={sub}
                    onAction={handleAction}
                    onOpenDetails={handleOpenDetails}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Inactive Strategies */}
          {inactiveSubscriptions.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Square className="h-5 w-5 text-gray-600" />
                Inactive ({inactiveSubscriptions.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {inactiveSubscriptions.map((sub) => (
                  <StrategyCard
                    key={sub.id}
                    subscription={sub}
                    onAction={handleAction}
                    onOpenDetails={handleOpenDetails}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Strategy Details Modal */}
      {selectedSubscription && (
        <StrategyDetailsModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          subscription={selectedSubscription}
          strategy={selectedSubscription.strategy}
          onActionComplete={fetchSubscriptions}
        />
      )}
    </div>
  )
}

interface StrategyCardProps {
  subscription: SubscriptionWithStrategy
  onAction: (subscriptionId: string, action: 'start' | 'pause' | 'stop') => Promise<void>
  onOpenDetails: (subscription: SubscriptionWithStrategy) => void
}

function StrategyCard({ subscription, onAction, onOpenDetails }: StrategyCardProps) {
  const router = useRouter()
  const [isActionLoading, setIsActionLoading] = useState(false)

  const handleAction = async (action: 'start' | 'pause' | 'stop') => {
    setIsActionLoading(true)
    try {
      await onAction(subscription.id, action)
    } finally {
      setIsActionLoading(false)
    }
  }

  const handleView = () => {
    router.push(`/dashboard/strategies/${subscription.strategy.slug}/monitor`)
  }

  const pnl = subscription.current_pnl || 0
  const todayPnl = subscription.today_pnl || 0
  const isProfitable = pnl >= 0
  const isTodayProfitable = todayPnl >= 0

  const statusColors = {
    active: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    paused: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
    inactive: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400',
    stopped: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Header - Clickable */}
      <div
        className="p-6 border-b border-gray-200 dark:border-gray-800 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
        onClick={() => onOpenDetails(subscription)}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="font-semibold text-lg mb-1">{subscription.strategy.name}</h3>
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span>{subscription.strategy.timeframe}</span>
              <span>•</span>
              <span>{subscription.is_paper_trading ? 'Paper' : 'Live'}</span>
              {subscription.selected_symbols && subscription.selected_symbols.length > 0 && (
                <>
                  <span>•</span>
                  <span className="font-mono text-xs">
                    {subscription.selected_symbols.slice(0, 2).join(', ')}
                    {subscription.selected_symbols.length > 2 && ` +${subscription.selected_symbols.length - 2}`}
                  </span>
                </>
              )}
            </div>
          </div>
          <span className={cn('px-3 py-1 text-xs font-medium rounded-full', statusColors[subscription.status])}>
            {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
          </span>
        </div>

        {/* P&L */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total P&L</p>
            <p className={cn('text-lg font-semibold flex items-center gap-1', isProfitable ? 'text-green-600' : 'text-red-600')}>
              {isProfitable ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
              {formatCurrency(Math.abs(pnl))}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Today P&L</p>
            <p className={cn('text-lg font-semibold flex items-center gap-1', isTodayProfitable ? 'text-green-600' : 'text-red-600')}>
              {isTodayProfitable ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
              {formatCurrency(Math.abs(todayPnl))}
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="p-6 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Capital</span>
          <span className="font-medium">{formatCurrency(subscription.capital_allocated)}</span>
        </div>
        <div className="flex items-start justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Symbols</span>
          <div className="flex flex-wrap gap-1 justify-end max-w-[60%]">
            {subscription.selected_symbols && subscription.selected_symbols.length > 0 ? (
              subscription.selected_symbols.slice(0, 2).map((symbol) => (
                <span
                  key={symbol}
                  className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded text-xs font-mono"
                >
                  {symbol}
                </span>
              ))
            ) : (
              <span className="font-medium">0</span>
            )}
            {subscription.selected_symbols && subscription.selected_symbols.length > 2 && (
              <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded text-xs">
                +{subscription.selected_symbols.length - 2}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 dark:text-gray-400">Max Positions</span>
          <span className="font-medium">{subscription.max_positions}</span>
        </div>
        {subscription.last_started_at && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400">Last Active</span>
            <span className="font-medium text-xs">
              {new Date(subscription.last_started_at).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 bg-gray-50 dark:bg-gray-800/50 flex items-center gap-2">
        {subscription.status === 'inactive' || subscription.status === 'stopped' ? (
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleAction('start')
            }}
            disabled={isActionLoading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Start
          </button>
        ) : subscription.status === 'paused' ? (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleAction('start')
              }}
              disabled={isActionLoading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Resume
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleAction('stop')
              }}
              disabled={isActionLoading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              <Square className="h-4 w-4" />
              Stop
            </button>
          </>
        ) : (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleAction('pause')
              }}
              disabled={isActionLoading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors disabled:opacity-50"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
              Pause
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleAction('stop')
              }}
              disabled={isActionLoading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              <Square className="h-4 w-4" />
              Stop
            </button>
          </>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleView()
          }}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          title="View Full Monitor"
        >
          <Eye className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
