'use client'

import { useState, useMemo, useEffect } from 'react'
import { X, RefreshCw, Calendar, Clock } from 'lucide-react'
import { StrategyChart } from '@/components/charts/StrategyChart'
import { cn } from '@/lib/utils'

interface ChartModalProps {
  isOpen: boolean
  onClose: () => void
  symbol: string
  subscriptionId: string
  availableSymbols?: string[]
  strategyTimeframe?: string
}

type TimeRangePreset = '1H' | '4H' | '1D' | '1W' | '1M' | 'CUSTOM' | 'LIVE'

export function ChartModal({
  isOpen,
  onClose,
  symbol: initialSymbol,
  subscriptionId,
  availableSymbols = [],
  strategyTimeframe = '15min',
}: ChartModalProps) {
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol)
  const [timeRange, setTimeRange] = useState<TimeRangePreset>('1D')
  const [customFromDate, setCustomFromDate] = useState<Date | undefined>(undefined)
  const [customToDate, setCustomToDate] = useState<Date | undefined>(undefined)
  const [refreshKey, setRefreshKey] = useState(0)

  // Sync selectedSymbol with initialSymbol when modal opens or symbol changes
  useEffect(() => {
    if (isOpen && initialSymbol) {
      setSelectedSymbol(initialSymbol)
      setRefreshKey((prev) => prev + 1)
    }
  }, [isOpen, initialSymbol])

  // Calculate date range based on preset
  const dateRange = useMemo(() => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

    switch (timeRange) {
      case '1H':
        // Last 1 hour
        return {
          from: new Date(now.getTime() - 60 * 60 * 1000),
          to: now,
        }
      case '4H':
        // Last 4 hours
        return {
          from: new Date(now.getTime() - 4 * 60 * 60 * 1000),
          to: now,
        }
      case '1D':
        // Today
        return {
          from: today,
          to: now,
        }
      case '1W':
        // Last 7 days
        return {
          from: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
          to: now,
        }
      case '1M':
        // Last 30 days
        return {
          from: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000),
          to: now,
        }
      case 'CUSTOM':
        return {
          from: customFromDate,
          to: customToDate,
        }
      case 'LIVE':
        // Last 200 candles (dynamic based on timeframe)
        const candleInterval = parseCandleInterval(strategyTimeframe)
        return {
          from: new Date(now.getTime() - 200 * candleInterval),
          to: now,
        }
      default:
        return {
          from: today,
          to: now,
        }
    }
  }, [timeRange, customFromDate, customToDate, strategyTimeframe])

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1)
  }

  const handleSymbolChange = (symbol: string) => {
    setSelectedSymbol(symbol)
    setRefreshKey((prev) => prev + 1)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-7xl h-[90vh] m-4 bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-800">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-semibold">Strategy Chart</h2>

            {/* Symbol Selector */}
            {availableSymbols.length > 1 && (
              <select
                value={selectedSymbol}
                onChange={(e) => handleSymbolChange(e.target.value)}
                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {availableSymbols.map((sym) => (
                  <option key={sym} value={sym}>
                    {sym}
                  </option>
                ))}
              </select>
            )}

            {/* Timeframe Badge */}
            <div className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md">
              <Clock className="h-3 w-3" />
              <span>{strategyTimeframe}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
              title="Refresh chart"
            >
              <RefreshCw className="h-5 w-5" />
            </button>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="p-4 border-b dark:border-gray-800">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-500 dark:text-gray-400 mr-2">Time Range:</span>

            {/* Preset Buttons */}
            {(['1H', '4H', '1D', '1W', '1M', 'LIVE'] as TimeRangePreset[]).map((preset) => (
              <button
                key={preset}
                onClick={() => setTimeRange(preset)}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-md transition-colors',
                  timeRange === preset
                    ? 'bg-primary text-white'
                    : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
                )}
              >
                {preset}
              </button>
            ))}

            {/* Custom Range Button */}
            <button
              onClick={() => setTimeRange('CUSTOM')}
              className={cn(
                'flex items-center gap-1 px-3 py-1.5 text-sm rounded-md transition-colors',
                timeRange === 'CUSTOM'
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
              )}
            >
              <Calendar className="h-4 w-4" />
              Custom
            </button>
          </div>

          {/* Custom Date Picker */}
          {timeRange === 'CUSTOM' && (
            <div className="mt-3 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 dark:text-gray-400">From:</label>
                <input
                  type="date"
                  value={customFromDate?.toISOString().split('T')[0] || ''}
                  onChange={(e) => setCustomFromDate(e.target.value ? new Date(e.target.value) : undefined)}
                  className="px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 dark:text-gray-400">To:</label>
                <input
                  type="date"
                  value={customToDate?.toISOString().split('T')[0] || ''}
                  onChange={(e) => setCustomToDate(e.target.value ? new Date(e.target.value) : undefined)}
                  className="px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          )}
        </div>

        {/* Chart Container */}
        <div className="flex-1 overflow-auto p-4">
          {selectedSymbol ? (
            <StrategyChart
              key={`${selectedSymbol}-${refreshKey}`}
              symbol={selectedSymbol}
              subscriptionId={subscriptionId}
              fromDate={dateRange.from}
              toDate={dateRange.to}
              height={500}
              showVolume={true}
              enableRealtime={timeRange === 'LIVE'}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <p>Please select a symbol to view the chart</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Helper function to parse candle interval to milliseconds
function parseCandleInterval(interval: string): number {
  const match = interval.match(/^(\d+)(min|hour|day)$/)
  if (!match) return 15 * 60 * 1000 // Default 15 minutes

  const value = parseInt(match[1])
  const unit = match[2]

  switch (unit) {
    case 'min':
      return value * 60 * 1000
    case 'hour':
      return value * 60 * 60 * 1000
    case 'day':
      return value * 24 * 60 * 60 * 1000
    default:
      return 15 * 60 * 1000
  }
}
