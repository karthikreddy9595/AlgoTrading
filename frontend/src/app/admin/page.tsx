'use client'

import { useEffect, useState } from 'react'
import {
  Activity,
  ShoppingCart,
  ArrowUpDown,
  TrendingUp,
  Wallet,
  AlertTriangle,
  Power,
  RefreshCw,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { formatCurrency, cn } from '@/lib/utils'
import { toast } from 'sonner'

interface DashboardData {
  active_strategies: number
  today_orders: number
  today_trades: number
  today_pnl: number
  total_capital: number
  timestamp: string
}

interface ActiveStrategy {
  id: string
  user_id: string
  strategy_id: string
  status: string
  capital_allocated: number
  is_paper_trading: boolean
  current_pnl: number
  today_pnl: number
  max_drawdown_percent: number
  last_started_at: string
  user?: { email: string; full_name: string }
  strategy?: { name: string }
}

interface Order {
  id: string
  symbol: string
  side: string
  quantity: number
  price: number
  status: string
  created_at: string
}

interface Trade {
  id: string
  symbol: string
  side: string
  quantity: number
  price: number
  pnl: number
  executed_at: string
}

interface KillSwitchStatus {
  global: boolean
  user_switches: string[]
  strategy_switches: string[]
}

export default function AdminDashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [activeStrategies, setActiveStrategies] = useState<ActiveStrategy[]>([])
  const [recentOrders, setRecentOrders] = useState<Order[]>([])
  const [recentTrades, setRecentTrades] = useState<Trade[]>([])
  const [killSwitch, setKillSwitch] = useState<KillSwitchStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isTogglingKillSwitch, setIsTogglingKillSwitch] = useState(false)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      const [dashboardData, strategiesData, ordersData, tradesData, killSwitchData] = await Promise.all([
        adminApi.getDashboard().catch(() => null),
        adminApi.getActiveStrategies().catch(() => []),
        adminApi.getRecentOrders(10).catch(() => []),
        adminApi.getRecentTrades(10).catch(() => []),
        adminApi.getKillSwitchStatus().catch(() => ({ global: false, user_switches: [], strategy_switches: [] })),
      ])
      setDashboard(dashboardData)
      setActiveStrategies(strategiesData || [])
      setRecentOrders(ordersData || [])
      setRecentTrades(tradesData || [])
      setKillSwitch(killSwitchData)
    } catch (error) {
      console.error('Failed to fetch admin data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggleKillSwitch = async () => {
    if (!killSwitch) return

    const confirmMessage = killSwitch.global
      ? 'Are you sure you want to DEACTIVATE the global kill switch? Trading will resume.'
      : 'Are you sure you want to ACTIVATE the global kill switch? ALL trading will stop immediately!'

    if (!confirm(confirmMessage)) return

    setIsTogglingKillSwitch(true)
    try {
      if (killSwitch.global) {
        await adminApi.deactivateKillSwitch('global')
        toast.success('Global kill switch deactivated')
      } else {
        await adminApi.activateKillSwitch('global')
        toast.success('Global kill switch activated - All trading stopped!')
      }
      await fetchData()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to toggle kill switch')
    } finally {
      setIsTogglingKillSwitch(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Platform monitoring and control
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Kill Switch Control */}
      <div className={cn(
        'rounded-xl border-2 p-6',
        killSwitch?.global
          ? 'bg-red-50 dark:bg-red-900/20 border-red-500'
          : 'bg-green-50 dark:bg-green-900/20 border-green-500'
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={cn(
              'p-3 rounded-full',
              killSwitch?.global ? 'bg-red-500' : 'bg-green-500'
            )}>
              <Power className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Global Kill Switch</h2>
              <p className={cn(
                'text-sm',
                killSwitch?.global ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
              )}>
                {killSwitch?.global ? 'ACTIVATED - All trading is stopped' : 'Trading is active'}
              </p>
            </div>
          </div>
          <button
            onClick={handleToggleKillSwitch}
            disabled={isTogglingKillSwitch}
            className={cn(
              'px-6 py-3 rounded-lg font-medium text-white transition-colors disabled:opacity-50',
              killSwitch?.global
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700'
            )}
          >
            {isTogglingKillSwitch ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            ) : killSwitch?.global ? (
              'Resume Trading'
            ) : (
              'Stop All Trading'
            )}
          </button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Active Strategies"
          value={String(dashboard?.active_strategies || 0)}
          icon={<Activity className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          title="Today's Orders"
          value={String(dashboard?.today_orders || 0)}
          icon={<ShoppingCart className="h-5 w-5" />}
          color="purple"
        />
        <StatCard
          title="Today's Trades"
          value={String(dashboard?.today_trades || 0)}
          icon={<ArrowUpDown className="h-5 w-5" />}
          color="indigo"
        />
        <StatCard
          title="Today's P&L"
          value={formatCurrency(dashboard?.today_pnl || 0)}
          icon={<TrendingUp className="h-5 w-5" />}
          color={(dashboard?.today_pnl || 0) >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Total Capital"
          value={formatCurrency(dashboard?.total_capital || 0)}
          icon={<Wallet className="h-5 w-5" />}
          color="blue"
        />
      </div>

      {/* Active Strategies */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <h2 className="text-lg font-semibold">Active Strategies</h2>
        </div>
        <div className="overflow-x-auto">
          {activeStrategies.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No active strategies
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                  <th className="px-6 py-3 font-medium">User</th>
                  <th className="px-6 py-3 font-medium">Strategy</th>
                  <th className="px-6 py-3 font-medium">Capital</th>
                  <th className="px-6 py-3 font-medium">Today's P&L</th>
                  <th className="px-6 py-3 font-medium">Total P&L</th>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {activeStrategies.slice(0, 10).map((strategy) => (
                  <tr key={strategy.id} className="text-sm">
                    <td className="px-6 py-4">
                      <div className="font-medium">{strategy.user?.full_name || 'Unknown'}</div>
                      <div className="text-xs text-gray-500">{strategy.user?.email}</div>
                    </td>
                    <td className="px-6 py-4">{strategy.strategy?.name || 'Unknown'}</td>
                    <td className="px-6 py-4">{formatCurrency(strategy.capital_allocated)}</td>
                    <td className={cn('px-6 py-4', strategy.today_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                      {formatCurrency(strategy.today_pnl)}
                    </td>
                    <td className={cn('px-6 py-4', strategy.current_pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                      {formatCurrency(strategy.current_pnl)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        'px-2 py-1 text-xs rounded',
                        strategy.is_paper_trading
                          ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                          : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                      )}>
                        {strategy.is_paper_trading ? 'Paper' : 'Live'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 capitalize">
                        {strategy.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Recent Orders and Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Orders */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-lg font-semibold">Recent Orders</h2>
          </div>
          <div className="overflow-x-auto">
            {recentOrders.length === 0 ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                No recent orders
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                    <th className="px-4 py-3 font-medium">Symbol</th>
                    <th className="px-4 py-3 font-medium">Side</th>
                    <th className="px-4 py-3 font-medium">Qty</th>
                    <th className="px-4 py-3 font-medium">Price</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {recentOrders.map((order) => (
                    <tr key={order.id} className="text-sm">
                      <td className="px-4 py-3 font-medium">{order.symbol}</td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          'px-2 py-0.5 text-xs rounded',
                          order.side === 'buy'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                        )}>
                          {order.side}
                        </span>
                      </td>
                      <td className="px-4 py-3">{order.quantity}</td>
                      <td className="px-4 py-3">{formatCurrency(order.price)}</td>
                      <td className="px-4 py-3 capitalize text-xs">{order.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Recent Trades */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-lg font-semibold">Recent Trades</h2>
          </div>
          <div className="overflow-x-auto">
            {recentTrades.length === 0 ? (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                No recent trades
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                    <th className="px-4 py-3 font-medium">Symbol</th>
                    <th className="px-4 py-3 font-medium">Side</th>
                    <th className="px-4 py-3 font-medium">Qty</th>
                    <th className="px-4 py-3 font-medium">Price</th>
                    <th className="px-4 py-3 font-medium">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {recentTrades.map((trade) => (
                    <tr key={trade.id} className="text-sm">
                      <td className="px-4 py-3 font-medium">{trade.symbol}</td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          'px-2 py-0.5 text-xs rounded',
                          trade.side === 'buy'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                        )}>
                          {trade.side}
                        </span>
                      </td>
                      <td className="px-4 py-3">{trade.quantity}</td>
                      <td className="px-4 py-3">{formatCurrency(trade.price)}</td>
                      <td className={cn('px-4 py-3', trade.pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                        {formatCurrency(trade.pnl)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string
  value: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'red' | 'purple' | 'indigo'
}) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
    indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>{icon}</div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}
