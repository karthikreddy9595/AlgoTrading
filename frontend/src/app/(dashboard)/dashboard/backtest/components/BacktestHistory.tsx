'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Trash2,
  Eye,
  RefreshCw,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'
import { backtestApi } from '@/lib/api'
import { BacktestListItem, BacktestStatus } from '@/types/backtest'
import { cn, formatCurrency, formatPercent } from '@/lib/utils'
import { format } from 'date-fns'
import { toast } from 'sonner'

export function BacktestHistory() {
  const router = useRouter()
  const [backtests, setBacktests] = useState<BacktestListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    fetchBacktests()
  }, [])

  const fetchBacktests = async () => {
    setIsLoading(true)
    try {
      const data = await backtestApi.getHistory({ limit: 50 })
      setBacktests(data || [])
    } catch (error) {
      console.error('Failed to fetch backtest history:', error)
      toast.error('Failed to load backtest history')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this backtest?')) return

    setDeletingId(id)
    try {
      await backtestApi.delete(id)
      setBacktests(backtests.filter((b) => b.id !== id))
      toast.success('Backtest deleted')
    } catch (error) {
      console.error('Failed to delete backtest:', error)
      toast.error('Failed to delete backtest')
    } finally {
      setDeletingId(null)
    }
  }

  const getStatusIcon = (status: BacktestStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-400" />
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'cancelled':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: BacktestStatus) => {
    const styles: Record<BacktestStatus, string> = {
      pending: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
      cancelled: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    }

    return (
      <span className={cn('flex items-center gap-1 px-2 py-1 text-xs rounded-full', styles[status])}>
        {getStatusIcon(status)}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (backtests.length === 0) {
    return (
      <div className="text-center py-12">
        <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium mb-2">No backtests yet</h3>
        <p className="text-gray-500 dark:text-gray-400">
          Run your first backtest to see it here
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">History</h2>
        <button
          onClick={fetchBacktests}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          title="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-3">
        {backtests.map((backtest) => (
          <div
            key={backtest.id}
            onClick={() => {
              if (backtest.status === 'completed') {
                router.push(`/dashboard/backtest/${backtest.id}`)
              }
            }}
            className={cn(
              'p-4 rounded-lg border border-gray-200 dark:border-gray-700 transition-colors',
              backtest.status === 'completed'
                ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50'
                : ''
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold">{backtest.symbol}</span>
                  <span className="text-xs text-gray-500">{backtest.exchange}</span>
                  {getStatusBadge(backtest.status)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {format(new Date(backtest.start_date), 'MMM d, yyyy')} -{' '}
                  {format(new Date(backtest.end_date), 'MMM d, yyyy')}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  Capital: {formatCurrency(backtest.initial_capital)} | Interval: {backtest.interval}
                </div>
              </div>

              {/* Results Summary for Completed */}
              {backtest.status === 'completed' && backtest.total_return_percent !== undefined && (
                <div className="text-right">
                  <div
                    className={cn(
                      'flex items-center gap-1 font-semibold',
                      backtest.total_return_percent >= 0 ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {backtest.total_return_percent >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    {formatPercent(backtest.total_return_percent)}
                  </div>
                  {backtest.total_trades !== undefined && (
                    <div className="text-xs text-gray-500">{backtest.total_trades} trades</div>
                  )}
                </div>
              )}

              {/* Progress for Running */}
              {backtest.status === 'running' && (
                <div className="text-right">
                  <div className="text-sm font-medium text-blue-600">{backtest.progress}%</div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2">
                {backtest.status === 'completed' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      router.push(`/dashboard/backtest/${backtest.id}`)
                    }}
                    className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
                    title="View Results"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={(e) => handleDelete(backtest.id, e)}
                  disabled={deletingId === backtest.id}
                  className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 disabled:opacity-50"
                  title="Delete"
                >
                  {deletingId === backtest.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Progress Bar for Running */}
            {backtest.status === 'running' && (
              <div className="mt-3">
                <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${backtest.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error Message for Failed */}
            {backtest.status === 'failed' && backtest.error_message && (
              <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <p className="text-xs text-red-600 dark:text-red-400 line-clamp-2">
                  {backtest.error_message}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
