'use client'

import { Fragment, useEffect, useState, useCallback } from 'react'
import { Dialog, Transition, Tab } from '@headlessui/react'
import {
  X,
  Play,
  Pause,
  Square,
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  BarChart3,
  Settings,
  Loader2,
  RefreshCw,
  Wifi,
  WifiOff,
  LineChart,
  Clock,
} from 'lucide-react'
import { strategyApi, portfolioApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'
import type { StrategySubscription, Strategy } from '@/types/strategy'
import { StrategyChart } from '@/components/charts/StrategyChart'
import { useStrategyWebSocket } from '@/hooks/useStrategyWebSocket'

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

interface StrategyDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  subscription: StrategySubscription
  strategy: Strategy
  onActionComplete?: () => void
}

export function StrategyDetailsModal({
  isOpen,
  onClose,
  subscription: initialSubscription,
  strategy,
  onActionComplete,
}: StrategyDetailsModalProps) {
  const [subscription, setSubscription] = useState(initialSubscription)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isActionLoading, setIsActionLoading] = useState(false)
  const [selectedChartSymbol, setSelectedChartSymbol] = useState<string>('')

  // WebSocket for real-time updates
  const wsState = useStrategyWebSocket({
    subscriptionId: subscription?.id || null,
    enabled: isOpen && !!subscription,
  })

  useEffect(() => {
    if (isOpen && subscription) {
      fetchDetails()
    }
  }, [isOpen, subscription?.id])

  useEffect(() => {
    setSubscription(initialSubscription)
  }, [initialSubscription])

  useEffect(() => {
    if (subscription.selected_symbols && subscription.selected_symbols.length > 0 && !selectedChartSymbol) {
      setSelectedChartSymbol(subscription.selected_symbols[0])
    }
  }, [subscription.selected_symbols, selectedChartSymbol])

  const fetchDetails = async () => {
    if (!subscription) return

    setIsLoading(true)
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
    } catch (error) {
      console.error('Failed to fetch details:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAction = async (action: 'start' | 'stop' | 'pause' | 'resume') => {
    if (!subscription) return

    setIsActionLoading(true)
    try {
      const updated = await strategyApi.subscriptionAction(subscription.id, action)
      setSubscription(updated)
      onActionComplete?.()
    } catch (err: any) {
      alert(err.response?.data?.detail || `Failed to ${action} strategy`)
    } finally {
      setIsActionLoading(false)
    }
  }

  const currentPnl = wsState.pnl || subscription.current_pnl || 0
  const todayPnl = wsState.todayPnl || subscription.today_pnl || 0
  const currentStatus = wsState.status !== 'unknown' ? wsState.status : subscription.status

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-6xl transform overflow-hidden rounded-2xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-2xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-yellow-500">
                      <Activity className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <Dialog.Title className="text-xl font-bold flex items-center gap-2">
                        {strategy.name}
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
                      </Dialog.Title>
                      <p className="text-sm text-gray-500 mt-1">
                        {strategy.timeframe} • Strategy Monitoring & Control
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'flex items-center gap-1 text-xs px-2 py-1 rounded-lg',
                      wsState.isConnected
                        ? 'text-green-600 bg-green-50 dark:bg-green-900/20'
                        : 'text-gray-400 bg-gray-50 dark:bg-gray-800'
                    )}>
                      {wsState.isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                      {wsState.isConnected ? 'Live' : 'Offline'}
                    </div>
                    <button
                      onClick={fetchDetails}
                      disabled={isLoading}
                      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                      title="Refresh data"
                    >
                      <RefreshCw className={cn('h-5 w-5', isLoading && 'animate-spin')} />
                    </button>
                    <button
                      onClick={onClose}
                      className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6 max-h-[calc(100vh-200px)] overflow-y-auto">
                  <Tab.Group>
                    <Tab.List className="flex space-x-1 rounded-xl bg-gray-100 dark:bg-gray-800 p-1 mb-6">
                      <Tab
                        className={({ selected }) =>
                          cn(
                            'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                            'ring-white ring-opacity-60 ring-offset-2 focus:outline-none focus:ring-2',
                            selected
                              ? 'bg-white dark:bg-gray-900 shadow text-purple-700 dark:text-purple-400'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-900/50'
                          )
                        }
                      >
                        Overview
                      </Tab>
                      <Tab
                        className={({ selected }) =>
                          cn(
                            'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                            'ring-white ring-opacity-60 ring-offset-2 focus:outline-none focus:ring-2',
                            selected
                              ? 'bg-white dark:bg-gray-900 shadow text-purple-700 dark:text-purple-400'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-900/50'
                          )
                        }
                      >
                        Charts
                      </Tab>
                      <Tab
                        className={({ selected }) =>
                          cn(
                            'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                            'ring-white ring-opacity-60 ring-offset-2 focus:outline-none focus:ring-2',
                            selected
                              ? 'bg-white dark:bg-gray-900 shadow text-purple-700 dark:text-purple-400'
                              : 'text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-900/50'
                          )
                        }
                      >
                        Configuration
                      </Tab>
                    </Tab.List>

                    <Tab.Panels>
                      {/* Overview Tab */}
                      <Tab.Panel className="space-y-4">
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
                                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                >
                                  <Play className="h-4 w-4" />
                                  Start Strategy
                                </button>
                              ) : currentStatus === 'active' ? (
                                <>
                                  <button
                                    onClick={() => handleAction('pause')}
                                    className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
                                  >
                                    <Pause className="h-4 w-4" />
                                    Pause
                                  </button>
                                  <button
                                    onClick={() => handleAction('stop')}
                                    className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                                  >
                                    <Square className="h-4 w-4" />
                                    Stop
                                  </button>
                                </>
                              ) : currentStatus === 'paused' ? (
                                <>
                                  <button
                                    onClick={() => handleAction('resume')}
                                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                  >
                                    <Play className="h-4 w-4" />
                                    Resume
                                  </button>
                                  <button
                                    onClick={() => handleAction('stop')}
                                    className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
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
                        <div className="grid grid-cols-4 gap-4">
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                              <DollarSign className="h-4 w-4" />
                              <span className="text-sm">Capital</span>
                            </div>
                            <p className="text-lg font-semibold">{formatCurrency(subscription.capital_allocated)}</p>
                          </div>

                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                              <TrendingUp className="h-4 w-4" />
                              <span className="text-sm">Today's P&L</span>
                            </div>
                            <p className={cn(
                              'text-lg font-semibold',
                              todayPnl >= 0 ? 'text-green-600' : 'text-red-600'
                            )}>
                              {formatCurrency(todayPnl)}
                            </p>
                          </div>

                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                              <BarChart3 className="h-4 w-4" />
                              <span className="text-sm">Total P&L</span>
                            </div>
                            <p className={cn(
                              'text-lg font-semibold',
                              currentPnl >= 0 ? 'text-green-600' : 'text-red-600'
                            )}>
                              {formatCurrency(currentPnl)}
                            </p>
                          </div>

                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <div className="flex items-center gap-2 text-gray-500 mb-1">
                              <Activity className="h-4 w-4" />
                              <span className="text-sm">Open Positions</span>
                            </div>
                            <p className="text-lg font-semibold">{positions.length} / {subscription.max_positions}</p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          {/* Open Positions */}
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <h4 className="font-medium flex items-center gap-2 mb-3">
                              <Activity className="h-4 w-4" />
                              Open Positions
                            </h4>
                            {positions.length === 0 ? (
                              <p className="text-gray-500 text-center py-4">No open positions</p>
                            ) : (
                              <div className="space-y-2">
                                {positions.map(position => (
                                  <div
                                    key={position.id}
                                    className="flex items-center justify-between p-2 bg-white dark:bg-gray-900 rounded-lg"
                                  >
                                    <div>
                                      <p className="font-medium text-sm">{position.symbol}</p>
                                      <p className="text-xs text-gray-500">
                                        {position.quantity} @ {formatCurrency(position.avg_price)}
                                      </p>
                                    </div>
                                    <div className="text-right">
                                      <p className={cn(
                                        'font-medium text-sm',
                                        (position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                                      )}>
                                        {formatCurrency(position.unrealized_pnl || 0)}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Recent Orders */}
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <h4 className="font-medium flex items-center gap-2 mb-3">
                              <Clock className="h-4 w-4" />
                              Recent Orders
                            </h4>
                            {orders.length === 0 ? (
                              <p className="text-gray-500 text-center py-4">No recent orders</p>
                            ) : (
                              <div className="space-y-2">
                                {orders.slice(0, 5).map(order => (
                                  <div
                                    key={order.id}
                                    className="flex items-center justify-between p-2 bg-white dark:bg-gray-900 rounded-lg"
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
                                        <span className="font-medium text-sm">{order.symbol}</span>
                                      </div>
                                    </div>
                                    <span className={cn(
                                      'px-1.5 py-0.5 rounded-full text-xs font-medium',
                                      order.status === 'FILLED' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200',
                                      order.status === 'PENDING' && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200',
                                      order.status === 'REJECTED' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200',
                                      order.status === 'CANCELLED' && 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
                                    )}>
                                      {order.status}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Trading Symbols */}
                        {subscription.selected_symbols && subscription.selected_symbols.length > 0 && (
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <h4 className="font-medium mb-3">Trading Symbols</h4>
                            <div className="flex flex-wrap gap-2">
                              {subscription.selected_symbols.map(symbol => (
                                <div
                                  key={symbol}
                                  className="px-3 py-1.5 bg-white dark:bg-gray-900 rounded-lg text-sm font-medium"
                                >
                                  {symbol}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </Tab.Panel>

                      {/* Charts Tab */}
                      <Tab.Panel className="space-y-4">
                        {/* Symbol Selector */}
                        {subscription.selected_symbols && subscription.selected_symbols.length > 0 && (
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Symbol:</span>
                            {subscription.selected_symbols.map(symbol => (
                              <button
                                key={symbol}
                                onClick={() => setSelectedChartSymbol(symbol)}
                                className={cn(
                                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
                                  selectedChartSymbol === symbol
                                    ? 'bg-purple-600 text-white shadow-lg'
                                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                                )}
                              >
                                {symbol}
                              </button>
                            ))}
                          </div>
                        )}

                        {/* Chart */}
                        {selectedChartSymbol && (
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <StrategyChart
                              symbol={selectedChartSymbol}
                              subscriptionId={subscription.id}
                              timeframe={strategy.timeframe}
                              height={500}
                            />
                          </div>
                        )}

                        {!selectedChartSymbol && (
                          <div className="text-center py-12 text-gray-500">
                            <LineChart className="h-12 w-12 mx-auto mb-2 opacity-50" />
                            <p>Select a symbol to view chart</p>
                          </div>
                        )}
                      </Tab.Panel>

                      {/* Configuration Tab */}
                      <Tab.Panel className="space-y-4">
                        {/* Risk Parameters */}
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                          <h4 className="font-medium mb-3 flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            Risk Parameters
                          </h4>
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
                          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                            <h4 className="font-medium mb-3 flex items-center gap-2">
                              <BarChart3 className="h-4 w-4" />
                              Strategy Parameters
                            </h4>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                              {Object.entries(subscription.config_params).map(([key, value]) => (
                                <div key={key}>
                                  <p className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                                  <p className="font-medium">{String(value)}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Subscription Details */}
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
                          <h4 className="font-medium mb-3">Subscription Details</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-gray-500">Subscription ID</p>
                              <p className="font-mono text-xs">{subscription.id}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Trading Mode</p>
                              <p className="font-medium">
                                {subscription.is_paper_trading ? 'Paper Trading' : 'Live Trading'}
                              </p>
                            </div>
                            {subscription.last_started_at && (
                              <div>
                                <p className="text-gray-500">Last Started</p>
                                <p className="font-medium">
                                  {new Date(subscription.last_started_at).toLocaleString()}
                                </p>
                              </div>
                            )}
                            {subscription.created_at && (
                              <div>
                                <p className="text-gray-500">Subscribed On</p>
                                <p className="font-medium">
                                  {new Date(subscription.created_at).toLocaleDateString()}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </Tab.Panel>
                    </Tab.Panels>
                  </Tab.Group>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
