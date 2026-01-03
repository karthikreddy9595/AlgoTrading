'use client'

import { useEffect, useState } from 'react'
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Package,
  Clock,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { portfolioApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn, getStatusColor } from '@/lib/utils'

interface PortfolioSummary {
  total_capital: number
  allocated_capital: number
  available_capital: number
  total_pnl: number
  today_pnl: number
  active_strategies: number
  open_positions: number
  total_trades: number
}

interface Position {
  id: string
  symbol: string
  exchange: string
  quantity: number
  avg_price: number
  ltp: number
  pnl: number
  pnl_percent: number
}

interface Order {
  id: string
  symbol: string
  exchange: string
  order_type: string
  side: string
  quantity: number
  price: number
  status: string
  created_at: string
}

interface Trade {
  id: string
  symbol: string
  exchange: string
  side: string
  quantity: number
  price: number
  pnl: number
  executed_at: string
}

type TabType = 'positions' | 'orders' | 'trades'

export default function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [activeTab, setActiveTab] = useState<TabType>('positions')
  const [isLoading, setIsLoading] = useState(true)
  const [ordersPage, setOrdersPage] = useState(1)
  const [tradesPage, setTradesPage] = useState(1)
  const [ordersTotal, setOrdersTotal] = useState(0)
  const [tradesTotal, setTradesTotal] = useState(0)
  const pageSize = 10

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (activeTab === 'orders') {
      fetchOrders()
    } else if (activeTab === 'trades') {
      fetchTrades()
    }
  }, [activeTab, ordersPage, tradesPage])

  const fetchData = async () => {
    try {
      const [summaryData, positionsData] = await Promise.all([
        portfolioApi.getSummary(),
        portfolioApi.getPositions(),
      ])
      setSummary(summaryData)
      setPositions(positionsData || [])
    } catch (error) {
      console.error('Failed to fetch portfolio data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchOrders = async () => {
    try {
      const data = await portfolioApi.getOrders({ page: ordersPage, page_size: pageSize })
      setOrders(data.orders || [])
      setOrdersTotal(data.total || 0)
    } catch (error) {
      console.error('Failed to fetch orders:', error)
    }
  }

  const fetchTrades = async () => {
    try {
      const data = await portfolioApi.getTrades({ page: tradesPage, page_size: pageSize })
      setTrades(data.trades || [])
      setTradesTotal(data.total || 0)
    } catch (error) {
      console.error('Failed to fetch trades:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  const tabs = [
    { id: 'positions' as TabType, label: 'Positions', icon: Package, count: positions.length },
    { id: 'orders' as TabType, label: 'Orders', icon: Clock, count: ordersTotal },
    { id: 'trades' as TabType, label: 'Trades', icon: ArrowUpDown, count: tradesTotal },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Manage your positions, orders, and trades
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Capital"
          value={formatCurrency(summary?.total_capital || 0)}
          subtitle={`Available: ${formatCurrency(summary?.available_capital || 0)}`}
          icon={<Wallet className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          title="Today's P&L"
          value={formatCurrency(summary?.today_pnl || 0)}
          change={summary?.today_pnl ? formatPercent((summary.today_pnl / (summary.total_capital || 1)) * 100) : '0%'}
          isPositive={(summary?.today_pnl || 0) >= 0}
          icon={(summary?.today_pnl || 0) >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          color={(summary?.today_pnl || 0) >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Total P&L"
          value={formatCurrency(summary?.total_pnl || 0)}
          change={summary?.total_pnl ? formatPercent((summary.total_pnl / (summary.total_capital || 1)) * 100) : '0%'}
          isPositive={(summary?.total_pnl || 0) >= 0}
          icon={<BarChart3 className="h-5 w-5" />}
          color={(summary?.total_pnl || 0) >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Open Positions"
          value={String(summary?.open_positions || 0)}
          subtitle={`${summary?.total_trades || 0} total trades`}
          icon={<Package className="h-5 w-5" />}
          color="purple"
        />
      </div>

      {/* Tabs and Content */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        {/* Tab navigation */}
        <div className="border-b border-gray-200 dark:border-gray-800">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm',
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                )}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
                {tab.count > 0 && (
                  <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-800">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab content */}
        <div className="p-6">
          {activeTab === 'positions' && (
            <PositionsTable positions={positions} />
          )}
          {activeTab === 'orders' && (
            <OrdersTable
              orders={orders}
              page={ordersPage}
              total={ordersTotal}
              pageSize={pageSize}
              onPageChange={setOrdersPage}
            />
          )}
          {activeTab === 'trades' && (
            <TradesTable
              trades={trades}
              page={tradesPage}
              total={tradesTotal}
              pageSize={pageSize}
              onPageChange={setTradesPage}
            />
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  change,
  subtitle,
  isPositive,
  icon,
  color,
}: {
  title: string
  value: string
  change?: string
  subtitle?: string
  isPositive?: boolean
  icon: React.ReactNode
  color: 'blue' | 'green' | 'red' | 'purple'
}) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>{icon}</div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {change && (
        <div className={cn('text-sm mt-1', isPositive ? 'text-green-600' : 'text-red-600')}>
          {change}
        </div>
      )}
      {subtitle && (
        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</div>
      )}
    </div>
  )
}

function PositionsTable({ positions }: { positions: Position[] }) {
  if (positions.length === 0) {
    return (
      <div className="text-center py-12">
        <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium mb-2">No open positions</h3>
        <p className="text-gray-500 dark:text-gray-400">
          Your open positions will appear here
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
            <th className="pb-3 font-medium">Symbol</th>
            <th className="pb-3 font-medium">Qty</th>
            <th className="pb-3 font-medium">Avg Price</th>
            <th className="pb-3 font-medium">LTP</th>
            <th className="pb-3 font-medium text-right">P&L</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
          {positions.map((position) => (
            <tr key={position.id} className="text-sm">
              <td className="py-4">
                <div className="font-medium">{position.symbol}</div>
                <div className="text-gray-500 dark:text-gray-400 text-xs">{position.exchange}</div>
              </td>
              <td className="py-4">{position.quantity}</td>
              <td className="py-4">{formatCurrency(position.avg_price)}</td>
              <td className="py-4">{formatCurrency(position.ltp)}</td>
              <td className="py-4 text-right">
                <div className={cn('font-medium', position.pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {formatCurrency(position.pnl)}
                </div>
                <div className={cn('text-xs', position.pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                  {formatPercent(position.pnl_percent || 0)}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OrdersTable({
  orders,
  page,
  total,
  pageSize,
  onPageChange,
}: {
  orders: Order[]
  page: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
}) {
  const totalPages = Math.ceil(total / pageSize)

  if (orders.length === 0 && page === 1) {
    return (
      <div className="text-center py-12">
        <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium mb-2">No orders yet</h3>
        <p className="text-gray-500 dark:text-gray-400">
          Your order history will appear here
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
              <th className="pb-3 font-medium">Time</th>
              <th className="pb-3 font-medium">Symbol</th>
              <th className="pb-3 font-medium">Type</th>
              <th className="pb-3 font-medium">Side</th>
              <th className="pb-3 font-medium">Qty</th>
              <th className="pb-3 font-medium">Price</th>
              <th className="pb-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
            {orders.map((order) => (
              <tr key={order.id} className="text-sm">
                <td className="py-4 text-gray-500 dark:text-gray-400">
                  {new Date(order.created_at).toLocaleString()}
                </td>
                <td className="py-4">
                  <div className="font-medium">{order.symbol}</div>
                  <div className="text-gray-500 dark:text-gray-400 text-xs">{order.exchange}</div>
                </td>
                <td className="py-4 capitalize">{order.order_type}</td>
                <td className="py-4">
                  <span className={cn(
                    'px-2 py-1 text-xs rounded capitalize',
                    order.side === 'buy' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                  )}>
                    {order.side}
                  </span>
                </td>
                <td className="py-4">{order.quantity}</td>
                <td className="py-4">{formatCurrency(order.price)}</td>
                <td className="py-4">
                  <span className={cn('px-2 py-1 text-xs rounded capitalize', getStatusColor(order.status))}>
                    {order.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
      )}
    </div>
  )
}

function TradesTable({
  trades,
  page,
  total,
  pageSize,
  onPageChange,
}: {
  trades: Trade[]
  page: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
}) {
  const totalPages = Math.ceil(total / pageSize)

  if (trades.length === 0 && page === 1) {
    return (
      <div className="text-center py-12">
        <ArrowUpDown className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium mb-2">No trades yet</h3>
        <p className="text-gray-500 dark:text-gray-400">
          Your trade history will appear here
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
              <th className="pb-3 font-medium">Time</th>
              <th className="pb-3 font-medium">Symbol</th>
              <th className="pb-3 font-medium">Side</th>
              <th className="pb-3 font-medium">Qty</th>
              <th className="pb-3 font-medium">Price</th>
              <th className="pb-3 font-medium text-right">P&L</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
            {trades.map((trade) => (
              <tr key={trade.id} className="text-sm">
                <td className="py-4 text-gray-500 dark:text-gray-400">
                  {new Date(trade.executed_at).toLocaleString()}
                </td>
                <td className="py-4">
                  <div className="font-medium">{trade.symbol}</div>
                  <div className="text-gray-500 dark:text-gray-400 text-xs">{trade.exchange}</div>
                </td>
                <td className="py-4">
                  <span className={cn(
                    'px-2 py-1 text-xs rounded capitalize',
                    trade.side === 'buy' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                  )}>
                    {trade.side}
                  </span>
                </td>
                <td className="py-4">{trade.quantity}</td>
                <td className="py-4">{formatCurrency(trade.price)}</td>
                <td className="py-4 text-right">
                  <span className={cn('font-medium', trade.pnl >= 0 ? 'text-green-600' : 'text-red-600')}>
                    {formatCurrency(trade.pnl)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
      )}
    </div>
  )
}

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}) {
  return (
    <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200 dark:border-gray-800">
      <div className="text-sm text-gray-500 dark:text-gray-400">
        Page {page} of {totalPages}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
