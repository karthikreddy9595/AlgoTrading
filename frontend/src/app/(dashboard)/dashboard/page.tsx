'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  Activity,
  BarChart3,
  ArrowRight,
  Play,
  Pause,
  AlertTriangle,
} from 'lucide-react'
import { portfolioApi, strategyApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn, getStatusColor } from '@/lib/utils'

interface PortfolioSummary {
  total_capital: number
  allocated_capital: number
  total_pnl: number
  today_pnl: number
  active_strategies: number
  open_positions: number
  total_trades: number
}

interface StrategySubscription {
  id: string
  strategy_id: string
  status: string
  capital_allocated: number
  current_pnl: number
  today_pnl: number
  is_paper_trading: boolean
  strategy?: {
    name: string
    description: string
  }
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [subscriptions, setSubscriptions] = useState<StrategySubscription[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [summaryData, subsData] = await Promise.all([
          portfolioApi.getSummary(),
          strategyApi.getMySubscriptions(),
        ])
        setSummary(summaryData)
        setSubscriptions(subsData)
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

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
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Overview of your trading portfolio
          </p>
        </div>
        <Link
          href="/dashboard/strategies"
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
        >
          Browse Strategies <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Capital"
          value={formatCurrency(summary?.total_capital || 0)}
          icon={<Wallet className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          title="Today's P&L"
          value={formatCurrency(summary?.today_pnl || 0)}
          change={summary?.today_pnl ? formatPercent((summary.today_pnl / (summary.total_capital || 1)) * 100) : '0%'}
          isPositive={(summary?.today_pnl || 0) >= 0}
          icon={summary?.today_pnl && summary.today_pnl >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          color={summary?.today_pnl && summary.today_pnl >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Total P&L"
          value={formatCurrency(summary?.total_pnl || 0)}
          change={summary?.total_pnl ? formatPercent((summary.total_pnl / (summary.total_capital || 1)) * 100) : '0%'}
          isPositive={(summary?.total_pnl || 0) >= 0}
          icon={<BarChart3 className="h-5 w-5" />}
          color={summary?.total_pnl && summary.total_pnl >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Active Strategies"
          value={String(summary?.active_strategies || 0)}
          subtitle={`${summary?.open_positions || 0} open positions`}
          icon={<Activity className="h-5 w-5" />}
          color="purple"
        />
      </div>

      {/* Active Strategies */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your Strategies</h2>
          <Link
            href="/dashboard/strategies"
            className="text-sm text-primary hover:underline"
          >
            View all
          </Link>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-800">
          {subscriptions.length === 0 ? (
            <div className="p-8 text-center">
              <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No strategies yet</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Subscribe to a strategy to start trading
              </p>
              <Link
                href="/dashboard/strategies"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
              >
                Browse Strategies <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            subscriptions.map((sub) => (
              <StrategyRow key={sub.id} subscription={sub} />
            ))
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-lg font-semibold">Recent Trades</h2>
          </div>
          <div className="p-6 text-center text-gray-500 dark:text-gray-400">
            <p>No trades yet</p>
          </div>
        </div>

        {/* Market Status */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-lg font-semibold">Market Status</h2>
          </div>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div>
              <span className="font-medium">Markets Closed</span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              NSE/BSE trading hours: 9:15 AM - 3:30 PM IST
            </p>
          </div>
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
        <div
          className={cn(
            'text-sm mt-1',
            isPositive ? 'text-green-600' : 'text-red-600'
          )}
        >
          {change}
        </div>
      )}
      {subtitle && (
        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {subtitle}
        </div>
      )}
    </div>
  )
}

function StrategyRow({ subscription }: { subscription: StrategySubscription }) {
  return (
    <div className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <BarChart3 className="h-5 w-5 text-primary" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">
              {subscription.strategy?.name || 'Strategy'}
            </span>
            {subscription.is_paper_trading && (
              <span className="px-2 py-0.5 text-xs rounded bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
                Paper
              </span>
            )}
            <span
              className={cn(
                'px-2 py-0.5 text-xs rounded capitalize',
                getStatusColor(subscription.status)
              )}
            >
              {subscription.status}
            </span>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Capital: {formatCurrency(subscription.capital_allocated)}
          </div>
        </div>
      </div>
      <div className="text-right">
        <div
          className={cn(
            'font-medium',
            subscription.today_pnl >= 0 ? 'text-green-600' : 'text-red-600'
          )}
        >
          {formatCurrency(subscription.today_pnl)}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Today's P&L
        </div>
      </div>
    </div>
  )
}
