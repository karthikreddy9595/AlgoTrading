'use client'

import { useEffect, useState } from 'react'
import {
  ArrowUpCircle,
  ArrowDownCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from 'lucide-react'
import { backtestApi } from '@/lib/api'
import { BacktestTrade, BacktestTradeList } from '@/types/backtest'
import { formatCurrency, formatPercent, cn } from '@/lib/utils'
import { format } from 'date-fns'

interface BacktestTradesListProps {
  backtestId: string
}

export function BacktestTradesList({ backtestId }: BacktestTradesListProps) {
  const [trades, setTrades] = useState<BacktestTrade[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  useEffect(() => {
    fetchTrades()
  }, [backtestId, page])

  const fetchTrades = async () => {
    setIsLoading(true)
    try {
      const data: BacktestTradeList = await backtestApi.getTrades(backtestId, {
        page,
        page_size: pageSize,
      })
      setTrades(data.trades)
      setTotalPages(data.total_pages)
      setTotal(data.total)
    } catch (error) {
      console.error('Failed to fetch trades:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getSignalIcon = (signal: string) => {
    if (signal === 'BUY' || signal === 'EXIT_SHORT') {
      return <ArrowUpCircle className="h-4 w-4 text-green-500" />
    }
    return <ArrowDownCircle className="h-4 w-4 text-red-500" />
  }

  const getSignalBadge = (signal: string) => {
    const isLong = signal === 'BUY' || signal === 'EXIT_SHORT'
    return (
      <span
        className={cn(
          'flex items-center gap-1 px-2 py-1 text-xs rounded-full',
          isLong
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
        )}
      >
        {getSignalIcon(signal)}
        {signal.replace('_', ' ')}
      </span>
    )
  }

  if (isLoading && trades.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (trades.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        No trades executed during this backtest
      </div>
    )
  }

  return (
    <div>
      {/* Trade Count */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-500 dark:text-gray-400">
          Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total} trades
        </span>
      </div>

      {/* Trades Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                Signal
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                Entry Time
              </th>
              <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                Entry Price
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                Exit Time
              </th>
              <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                Exit Price
              </th>
              <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                Qty
              </th>
              <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                P&L
              </th>
              <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">
                P&L %
              </th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr
                key={trade.id}
                className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
              >
                <td className="py-3 px-4">{getSignalBadge(trade.signal)}</td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-300">
                  {format(new Date(trade.entry_time), 'MMM d, yyyy HH:mm')}
                </td>
                <td className="py-3 px-4 text-right font-medium">
                  {formatCurrency(trade.entry_price)}
                </td>
                <td className="py-3 px-4 text-gray-600 dark:text-gray-300">
                  {trade.exit_time
                    ? format(new Date(trade.exit_time), 'MMM d, yyyy HH:mm')
                    : trade.is_open
                    ? 'Open'
                    : '-'}
                </td>
                <td className="py-3 px-4 text-right font-medium">
                  {trade.exit_price ? formatCurrency(trade.exit_price) : '-'}
                </td>
                <td className="py-3 px-4 text-right">{trade.quantity}</td>
                <td
                  className={cn(
                    'py-3 px-4 text-right font-medium',
                    trade.pnl !== undefined && trade.pnl !== null
                      ? trade.pnl >= 0
                        ? 'text-green-600'
                        : 'text-red-600'
                      : ''
                  )}
                >
                  {trade.pnl !== undefined && trade.pnl !== null ? formatCurrency(trade.pnl) : '-'}
                </td>
                <td
                  className={cn(
                    'py-3 px-4 text-right font-medium',
                    trade.pnl_percent !== undefined && trade.pnl_percent !== null
                      ? trade.pnl_percent >= 0
                        ? 'text-green-600'
                        : 'text-red-600'
                      : ''
                  )}
                >
                  {trade.pnl_percent !== undefined && trade.pnl_percent !== null
                    ? formatPercent(trade.pnl_percent)
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages || isLoading}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  )
}
