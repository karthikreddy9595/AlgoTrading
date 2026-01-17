'use client'

import {
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  BarChart3,
  Clock,
  DollarSign,
  Percent,
  AlertTriangle,
} from 'lucide-react'
import { BacktestResult } from '@/types/backtest'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'

// Helper to safely convert value to number and format
const toNum = (value: unknown): number => {
  if (typeof value === 'number') return value
  if (typeof value === 'string') return parseFloat(value) || 0
  return 0
}

interface BacktestResultsMetricsProps {
  results: BacktestResult
  initialCapital: number
}

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  color: 'green' | 'red' | 'blue' | 'purple' | 'orange' | 'gray'
  isPositive?: boolean
}

function MetricCard({ title, value, subtitle, icon, color, isPositive }: MetricCardProps) {
  const colorClasses = {
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400',
    gray: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>{icon}</div>
      </div>
      <div
        className={cn(
          'text-2xl font-bold',
          isPositive !== undefined && (isPositive ? 'text-green-600' : 'text-red-600')
        )}
      >
        {value}
      </div>
      {subtitle && <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</div>}
    </div>
  )
}

export function BacktestResultsMetrics({ results, initialCapital }: BacktestResultsMetricsProps) {
  const totalReturn = toNum(results.total_return)
  const totalReturnPercent = toNum(results.total_return_percent)
  const isProfit = totalReturn >= 0

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`
    return `${Math.round(seconds / 86400)}d`
  }

  return (
    <div className="space-y-6">
      {/* Primary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Return"
          value={formatCurrency(totalReturn)}
          subtitle={formatPercent(totalReturnPercent)}
          icon={isProfit ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          color={isProfit ? 'green' : 'red'}
          isPositive={isProfit}
        />
        <MetricCard
          title="Final Capital"
          value={formatCurrency(results.final_capital ?? initialCapital)}
          subtitle={`Initial: ${formatCurrency(initialCapital)}`}
          icon={<DollarSign className="h-5 w-5" />}
          color="blue"
        />
        <MetricCard
          title="Win Rate"
          value={formatPercent(toNum(results.win_rate))}
          subtitle={`${results.winning_trades}W / ${results.losing_trades}L`}
          icon={<Target className="h-5 w-5" />}
          color={toNum(results.win_rate) >= 50 ? 'green' : 'orange'}
        />
        <MetricCard
          title="Total Trades"
          value={results.total_trades}
          subtitle={`Avg Duration: ${formatDuration(results.avg_trade_duration)}`}
          icon={<Activity className="h-5 w-5" />}
          color="purple"
        />
      </div>

      {/* Risk Metrics */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Risk Metrics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            title="Max Drawdown"
            value={formatPercent(toNum(results.max_drawdown))}
            icon={<AlertTriangle className="h-5 w-5" />}
            color="red"
          />
          <MetricCard
            title="Avg Drawdown"
            value={formatPercent(toNum(results.avg_drawdown))}
            icon={<BarChart3 className="h-5 w-5" />}
            color="orange"
          />
          <MetricCard
            title="Sharpe Ratio"
            value={toNum(results.sharpe_ratio).toFixed(2)}
            icon={<Percent className="h-5 w-5" />}
            color={toNum(results.sharpe_ratio) >= 1 ? 'green' : 'gray'}
          />
          <MetricCard
            title="Sortino Ratio"
            value={toNum(results.sortino_ratio).toFixed(2)}
            icon={<Percent className="h-5 w-5" />}
            color={toNum(results.sortino_ratio) >= 1 ? 'green' : 'gray'}
          />
        </div>
      </div>

      {/* Additional Metrics */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
          Additional Metrics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            title="CAGR"
            value={formatPercent(toNum(results.cagr))}
            icon={<TrendingUp className="h-5 w-5" />}
            color={toNum(results.cagr) >= 0 ? 'green' : 'red'}
          />
          <MetricCard
            title="Profit Factor"
            value={toNum(results.profit_factor).toFixed(2)}
            icon={<BarChart3 className="h-5 w-5" />}
            color={toNum(results.profit_factor) >= 1 ? 'green' : 'red'}
          />
          <MetricCard
            title="Calmar Ratio"
            value={toNum(results.calmar_ratio).toFixed(2)}
            icon={<Activity className="h-5 w-5" />}
            color={toNum(results.calmar_ratio) >= 1 ? 'green' : 'gray'}
          />
          <MetricCard
            title="Max Capital"
            value={formatCurrency(toNum(results.max_capital))}
            icon={<DollarSign className="h-5 w-5" />}
            color="blue"
          />
        </div>
      </div>
    </div>
  )
}
