'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Play,
  Pause,
  Square,
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  DollarSign,
  BarChart3,
  AlertCircle,
  Loader2,
  RefreshCw,
  Settings,
  Wifi,
  WifiOff,
  LineChart,
} from 'lucide-react'
import { strategyApi, portfolioApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import { useStrategyWebSocket } from '@/hooks/useStrategyWebSocket'
import type { StrategySubscription, Strategy } from '@/types/strategy'
import { ChartModal } from './components/ChartModal'

interface Position {
  id: string
  symbol: string
  exchange: string
  quantity: number
  avg_price: number
  current_price: number | null
  unrealized_pnl: number | null
}

interface Order {
  id: string
  symbol: string
  exchange: string
  order_type: string
  transaction_type: string
  quantity: number
  price: number | null
  status: string
  created_at: string
}

export default function StrategyMonitorPage() {
  const { slug } = useParams()
  const router = useRouter()

  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [subscription, setSubscription] = useState<StrategySubscription | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isActionLoading, setIsActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isChartModalOpen, setIsChartModalOpen] = useState(false)
  const [selectedChartSymbol, setSelectedChartSymbol] = useState<string>('')

  // WebSocket for real-time updates
  const wsState = useStrategyWebSocket({
    subscriptionId: subscription?.id || null,
    enabled: !!subscription,
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch strategy by slug
        const strategyData = await strategyApi.getBySlug(slug as string)
        setStrategy(strategyData)

        // Get user's subscription to this strategy
        const subs = await strategyApi.getMySubscriptions()
        const existingSub = subs.find((s: StrategySubscription) => s.strategy_id === strategyData.id)

        if (!existingSub) {
          setError('You are not subscribed to this strategy')
          setIsLoading(false)
          return
        }

        setSubscription(existingSub)

        // Fetch positions and orders
        const [positionsData, ordersData] = await Promise.all([
          portfolioApi.getPositions(),
          portfolioApi.getOrders({ page_size: 20 }),
        ])

        // Filter for this subscription
        setPositions(positionsData.filter((p: Position) =>
          existingSub.selected_symbols?.some((s: string) => s.includes(p.symbol))
        ))
        setOrders(ordersData.orders || [])

      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load monitor data')
      } finally {
        setIsLoading(false)
      }
    }

    if (slug) {
      fetchData()
    }
  }, [slug])

  const handleAction = async (action: 'start' | 'stop' | 'pause' | 'resume') => {
    if (!subscription) return

    setIsActionLoading(true)
    try {
      const updated = await strategyApi.subscriptionAction(subscription.id, action)
      setSubscription(updated)
    } catch (err: any) {
      alert(err.response?.data?.detail || `Failed to ${action} strategy`)
    } finally {
      setIsActionLoading(false)
    }
  }

  const refreshData = async () => {
    if (!subscription) return

    try {
      const [sub, positionsData, ordersData] = await Promise.all([
        strategyApi.getSubscription(subscription.id),
        portfolioApi.getPositions(),
        portfolioApi.getOrders({ page_size: 20 }),
      ])

      setSubscription(sub)
      setPositions(positionsData.filter((p: Position) =>
        sub.selected_symbols?.some((s: string) => s.includes(p.symbol))
      ))
      setOrders(ordersData.orders || [])
    } catch (err) {
      console.error('Failed to refresh data:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !subscription) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">{error || 'Subscription not found'}</p>
        <Link href={`/dashboard/strategies/${slug}`} className="text-blue-600 hover:underline mt-4 inline-block">
          Back to Strategy
        </Link>
      </div>
    )
  }

  const currentPnl = wsState.pnl || subscription.current_pnl
  const todayPnl = wsState.todayPnl || subscription.today_pnl
  const currentStatus = wsState.status !== 'unknown' ? wsState.status : subscription.status

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/dashboard/strategies/${slug}`}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{strategy?.name || 'Strategy Monitor'}</h1>
              <span className={cn(
                'px-2 py-1 rounded-full text-xs font-medium',
                currentStatus === 'active' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
                currentStatus === 'paused' && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
                currentStatus === 'stopped' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
                currentStatus === 'inactive' && 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
              )}>
                {currentStatus}
              </span>
              {subscription.is_paper_trading && (
                <span className="px-2 py-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded-full text-xs">
                  Paper Trading
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">Real-time strategy monitoring</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* WebSocket Status */}
          <div className={cn(
            'flex items-center gap-1 text-xs',
            wsState.isConnected ? 'text-green-600' : 'text-gray-400'
          )}>
            {wsState.isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {wsState.isConnected ? 'Live' : 'Offline'}
          </div>

          <button
            onClick={refreshData}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Refresh data"
          >
            <RefreshCw className="h-5 w-5" />
          </button>

          <Link
            href={`/dashboard/strategies/${slug}`}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Settings"
          >
            <Settings className="h-5 w-5" />
          </Link>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        {isActionLoading ? (
          <div className="flex items-center gap-2 text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing...
          </div>
        ) : (
          <>
            {currentStatus === 'inactive' || currentStatus === 'stopped' ? (
              <button
                onClick={() => handleAction('start')}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
              >
                <Play className="h-4 w-4" />
                Start Strategy
              </button>
            ) : currentStatus === 'active' ? (
              <>
                <button
                  onClick={() => handleAction('pause')}
                  className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg"
                >
                  <Pause className="h-4 w-4" />
                  Pause
                </button>
                <button
                  onClick={() => handleAction('stop')}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              </>
            ) : currentStatus === 'paused' ? (
              <>
                <button
                  onClick={() => handleAction('resume')}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
                >
                  <Play className="h-4 w-4" />
                  Resume
                </button>
                <button
                  onClick={() => handleAction('stop')}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              </>
            ) : null}
          </>
        )}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <DollarSign className="h-4 w-4" />
            <span className="text-sm">Capital</span>
          </div>
          <p className="text-xl font-semibold">{formatCurrency(subscription.capital_allocated)}</p>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <TrendingUp className="h-4 w-4" />
            <span className="text-sm">Today's P&L</span>
          </div>
          <p className={cn(
            'text-xl font-semibold',
            todayPnl >= 0 ? 'text-green-600' : 'text-red-600'
          )}>
            {formatCurrency(todayPnl)}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <BarChart3 className="h-4 w-4" />
            <span className="text-sm">Total P&L</span>
          </div>
          <p className={cn(
            'text-xl font-semibold',
            currentPnl >= 0 ? 'text-green-600' : 'text-red-600'
          )}>
            {formatCurrency(currentPnl)}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <Activity className="h-4 w-4" />
            <span className="text-sm">Open Positions</span>
          </div>
          <p className="text-xl font-semibold">{positions.length} / {subscription.max_positions}</p>
        </div>
      </div>

      {/* Selected Symbols */}
      {subscription.selected_symbols && subscription.selected_symbols.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <h3 className="font-medium mb-3">Trading Symbols</h3>
          <div className="flex flex-wrap gap-2">
            {subscription.selected_symbols.map(symbol => (
              <div
                key={symbol}
                className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-medium"
              >
                <span>{symbol}</span>
                <button
                  onClick={() => {
                    setSelectedChartSymbol(symbol)
                    setIsChartModalOpen(true)
                  }}
                  className="ml-1 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                  title={`View ${symbol} chart`}
                >
                  <LineChart className="h-4 w-4 text-primary" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Positions */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <h3 className="font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Open Positions
            </h3>
          </div>
          <div className="p-4">
            {positions.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No open positions</p>
            ) : (
              <div className="space-y-3">
                {positions.map(position => (
                  <div
                    key={position.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{position.symbol}</p>
                      <p className="text-sm text-gray-500">
                        {position.quantity} @ {formatCurrency(position.avg_price)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={cn(
                        'font-medium',
                        (position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                      )}>
                        {formatCurrency(position.unrealized_pnl || 0)}
                      </p>
                      {position.current_price && (
                        <p className="text-sm text-gray-500">
                          LTP: {formatCurrency(position.current_price)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Recent Orders */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <h3 className="font-semibold flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Recent Orders
            </h3>
          </div>
          <div className="p-4">
            {orders.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No recent orders</p>
            ) : (
              <div className="space-y-3">
                {orders.slice(0, 10).map(order => (
                  <div
                    key={order.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          'px-1.5 py-0.5 rounded text-xs font-medium',
                          order.transaction_type === 'BUY'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200'
                            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200'
                        )}>
                          {order.transaction_type}
                        </span>
                        <span className="font-medium">{order.symbol}</span>
                      </div>
                      <p className="text-sm text-gray-500">
                        {order.quantity} @ {order.price ? formatCurrency(order.price) : 'Market'}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={cn(
                        'px-2 py-1 rounded-full text-xs font-medium',
                        order.status === 'FILLED' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
                        order.status === 'PENDING' && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
                        order.status === 'REJECTED' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
                        order.status === 'CANCELLED' && 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
                      )}>
                        {order.status}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(order.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Activity Log from WebSocket */}
      {wsState.events.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="p-4 border-b border-gray-200 dark:border-gray-800">
            <h3 className="font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Live Activity
            </h3>
          </div>
          <div className="p-4 max-h-64 overflow-y-auto">
            <div className="space-y-2">
              {wsState.events.map((event, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 text-sm p-2 bg-gray-50 dark:bg-gray-800/50 rounded"
                >
                  <span className="text-gray-400 text-xs">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={cn(
                    'px-1.5 py-0.5 rounded text-xs font-medium',
                    event.type === 'order' && 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200',
                    event.type === 'position' && 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200',
                  )}>
                    {event.type}
                  </span>
                  <span className="text-gray-600 dark:text-gray-400">
                    {JSON.stringify(event.data).slice(0, 100)}...
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Risk Parameters */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
        <h3 className="font-medium mb-3">Risk Parameters</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Max Drawdown</p>
            <p className="font-medium">{subscription.max_drawdown_percent}%</p>
          </div>
          <div>
            <p className="text-gray-500">Daily Loss Limit</p>
            <p className="font-medium">
              {subscription.daily_loss_limit ? formatCurrency(subscription.daily_loss_limit) : 'Not set'}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Per Trade SL</p>
            <p className="font-medium">{subscription.per_trade_stop_loss_percent}%</p>
          </div>
          <div>
            <p className="text-gray-500">Max Positions</p>
            <p className="font-medium">{subscription.max_positions}</p>
          </div>
        </div>
      </div>

      {/* Strategy Parameters */}
      {subscription.config_params && Object.keys(subscription.config_params).length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
          <h3 className="font-medium mb-3">Strategy Parameters</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {Object.entries(subscription.config_params).map(([key, value]) => (
              <div key={key}>
                <p className="text-gray-500">{key.replace(/_/g, ' ')}</p>
                <p className="font-medium">{String(value)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Chart Modal */}
      <ChartModal
        isOpen={isChartModalOpen}
        onClose={() => setIsChartModalOpen(false)}
        symbol={selectedChartSymbol}
        subscriptionId={subscription.id}
        availableSymbols={subscription.selected_symbols || []}
        strategyTimeframe={strategy?.timeframe || '15min'}
      />
    </div>
  )
}
