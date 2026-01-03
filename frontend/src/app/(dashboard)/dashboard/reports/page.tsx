'use client'

import { useEffect, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Download,
  FileText,
  Calendar,
  Target,
  Activity,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { reportsApi } from '@/lib/api'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import { format, subDays } from 'date-fns'
import { toast } from 'sonner'

interface PerformanceData {
  total_pnl: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_trade_pnl: number
  max_drawdown: number
  sharpe_ratio: number
  daily_pnl: Array<{ date: string; pnl: number; cumulative_pnl: number }>
}

export default function ReportsPage() {
  const [performance, setPerformance] = useState<PerformanceData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [isDownloading, setIsDownloading] = useState<string | null>(null)

  useEffect(() => {
    fetchPerformance()
  }, [startDate, endDate])

  const fetchPerformance = async () => {
    setIsLoading(true)
    try {
      const data = await reportsApi.getPerformance({ start_date: startDate, end_date: endDate })
      setPerformance(data)
    } catch (error) {
      console.error('Failed to fetch performance data:', error)
      // Set default data if API fails
      setPerformance({
        total_pnl: 0,
        total_trades: 0,
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0,
        avg_trade_pnl: 0,
        max_drawdown: 0,
        sharpe_ratio: 0,
        daily_pnl: [],
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownload = async (type: 'trades-csv' | 'orders-csv' | 'portfolio-pdf') => {
    setIsDownloading(type)
    try {
      let blob: Blob
      let filename: string

      switch (type) {
        case 'trades-csv':
          blob = await reportsApi.downloadTradesCsv({ start_date: startDate, end_date: endDate })
          filename = `trades_${startDate}_${endDate}.csv`
          break
        case 'orders-csv':
          blob = await reportsApi.downloadOrdersCsv({ start_date: startDate, end_date: endDate })
          filename = `orders_${startDate}_${endDate}.csv`
          break
        case 'portfolio-pdf':
          blob = await reportsApi.downloadPortfolioPdf()
          filename = `portfolio_report_${format(new Date(), 'yyyy-MM-dd')}.pdf`
          break
      }

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      toast.success(`Downloaded ${filename}`)
    } catch (error) {
      console.error('Download failed:', error)
      toast.error('Download failed. Please try again.')
    } finally {
      setIsDownloading(null)
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
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Performance analytics and exports
          </p>
        </div>
      </div>

      {/* Date Range Picker */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-500 dark:text-gray-400">Date Range:</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2 ml-auto">
            <button
              onClick={() => {
                setStartDate(format(subDays(new Date(), 7), 'yyyy-MM-dd'))
                setEndDate(format(new Date(), 'yyyy-MM-dd'))
              }}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              7 Days
            </button>
            <button
              onClick={() => {
                setStartDate(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
                setEndDate(format(new Date(), 'yyyy-MM-dd'))
              }}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              30 Days
            </button>
            <button
              onClick={() => {
                setStartDate(format(subDays(new Date(), 90), 'yyyy-MM-dd'))
                setEndDate(format(new Date(), 'yyyy-MM-dd'))
              }}
              className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              90 Days
            </button>
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total P&L"
          value={formatCurrency(performance?.total_pnl || 0)}
          isPositive={(performance?.total_pnl || 0) >= 0}
          icon={(performance?.total_pnl || 0) >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
          color={(performance?.total_pnl || 0) >= 0 ? 'green' : 'red'}
        />
        <StatCard
          title="Win Rate"
          value={formatPercent(performance?.win_rate || 0)}
          subtitle={`${performance?.winning_trades || 0}W / ${performance?.losing_trades || 0}L`}
          icon={<Target className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          title="Total Trades"
          value={String(performance?.total_trades || 0)}
          subtitle={`Avg P&L: ${formatCurrency(performance?.avg_trade_pnl || 0)}`}
          icon={<Activity className="h-5 w-5" />}
          color="purple"
        />
        <StatCard
          title="Max Drawdown"
          value={formatPercent(performance?.max_drawdown || 0)}
          subtitle={`Sharpe: ${(performance?.sharpe_ratio || 0).toFixed(2)}`}
          icon={<BarChart3 className="h-5 w-5" />}
          color="red"
        />
      </div>

      {/* P&L Chart */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Cumulative P&L</h2>
        {performance?.daily_pnl && performance.daily_pnl.length > 0 ? (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={performance.daily_pnl}>
                <defs>
                  <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="date"
                  stroke="#6B7280"
                  fontSize={12}
                  tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                />
                <YAxis
                  stroke="#6B7280"
                  fontSize={12}
                  tickFormatter={(value) => formatCurrency(value)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                  }}
                  labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
                  formatter={(value: number) => [formatCurrency(value), 'P&L']}
                />
                <Area
                  type="monotone"
                  dataKey="cumulative_pnl"
                  stroke="#10B981"
                  fillOpacity={1}
                  fill="url(#colorPnl)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-80 flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No performance data available for the selected period</p>
            </div>
          </div>
        )}
      </div>

      {/* Daily P&L Chart */}
      {performance?.daily_pnl && performance.daily_pnl.length > 0 && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Daily P&L</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={performance.daily_pnl}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="date"
                  stroke="#6B7280"
                  fontSize={12}
                  tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                />
                <YAxis
                  stroke="#6B7280"
                  fontSize={12}
                  tickFormatter={(value) => formatCurrency(value)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                  }}
                  labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
                  formatter={(value: number) => [formatCurrency(value), 'Daily P&L']}
                />
                <Line
                  type="monotone"
                  dataKey="pnl"
                  stroke="#6366F1"
                  strokeWidth={2}
                  dot={{ fill: '#6366F1', strokeWidth: 0, r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Download Section */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-4">Export Reports</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <DownloadCard
            title="Trades Report"
            description="Download all trades as CSV"
            icon={<FileText className="h-6 w-6" />}
            onClick={() => handleDownload('trades-csv')}
            isLoading={isDownloading === 'trades-csv'}
          />
          <DownloadCard
            title="Orders Report"
            description="Download all orders as CSV"
            icon={<FileText className="h-6 w-6" />}
            onClick={() => handleDownload('orders-csv')}
            isLoading={isDownloading === 'orders-csv'}
          />
          <DownloadCard
            title="Portfolio Summary"
            description="Download portfolio as PDF"
            icon={<FileText className="h-6 w-6" />}
            onClick={() => handleDownload('portfolio-pdf')}
            isLoading={isDownloading === 'portfolio-pdf'}
          />
        </div>
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  subtitle,
  isPositive,
  icon,
  color,
}: {
  title: string
  value: string
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
      <div className={cn(
        'text-2xl font-bold',
        isPositive !== undefined && (isPositive ? 'text-green-600' : 'text-red-600')
      )}>
        {value}
      </div>
      {subtitle && (
        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</div>
      )}
    </div>
  )
}

function DownloadCard({
  title,
  description,
  icon,
  onClick,
  isLoading,
}: {
  title: string
  description: string
  icon: React.ReactNode
  onClick: () => void
  isLoading: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className="flex items-center gap-4 p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <div className="p-3 rounded-lg bg-primary/10 text-primary">
        {isLoading ? (
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
        ) : (
          icon
        )}
      </div>
      <div className="flex-1">
        <div className="font-medium">{title}</div>
        <div className="text-sm text-gray-500 dark:text-gray-400">{description}</div>
      </div>
      <Download className="h-5 w-5 text-gray-400" />
    </button>
  )
}
