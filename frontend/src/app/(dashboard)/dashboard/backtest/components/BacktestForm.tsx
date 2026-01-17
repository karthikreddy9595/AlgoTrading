'use client'

import { useState, useEffect } from 'react'
import { Calendar, Play, DollarSign, Clock, TrendingUp } from 'lucide-react'
import { strategyApi, backtestApi } from '@/lib/api'
import { BacktestInterval } from '@/types/backtest'
import { format, subDays } from 'date-fns'
import { toast } from 'sonner'

interface Strategy {
  id: string
  name: string
  slug: string
  description?: string
}

interface BacktestFormProps {
  onBacktestStarted: (backtestId: string) => void
}

const intervals: { value: BacktestInterval; label: string }[] = [
  { value: '1min', label: '1 Minute' },
  { value: '5min', label: '5 Minutes' },
  { value: '15min', label: '15 Minutes' },
  { value: '30min', label: '30 Minutes' },
  { value: '1hour', label: '1 Hour' },
  { value: '1day', label: '1 Day' },
]

const exchanges = [
  { value: 'NSE', label: 'NSE' },
  { value: 'BSE', label: 'BSE' },
  { value: 'NFO', label: 'NFO' },
]

export function BacktestForm({ onBacktestStarted }: BacktestFormProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [isLoadingStrategies, setIsLoadingStrategies] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [strategyId, setStrategyId] = useState('')
  const [symbol, setSymbol] = useState('')
  const [exchange, setExchange] = useState('NSE')
  const [interval, setInterval] = useState<BacktestInterval>('1day')
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 365), 'yyyy-MM-dd'))
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [initialCapital, setInitialCapital] = useState(100000)

  useEffect(() => {
    fetchStrategies()
  }, [])

  const fetchStrategies = async () => {
    try {
      const data = await strategyApi.list({ limit: 100 })
      setStrategies(data.strategies || data || [])
      if (data.strategies?.length > 0 || data?.length > 0) {
        const strats = data.strategies || data
        setStrategyId(strats[0].id)
      }
    } catch (error) {
      console.error('Failed to fetch strategies:', error)
      toast.error('Failed to load strategies')
    } finally {
      setIsLoadingStrategies(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!strategyId) {
      toast.error('Please select a strategy')
      return
    }

    if (!symbol.trim()) {
      toast.error('Please enter a stock symbol')
      return
    }

    if (new Date(startDate) >= new Date(endDate)) {
      toast.error('End date must be after start date')
      return
    }

    setIsSubmitting(true)
    try {
      const response = await backtestApi.run({
        strategy_id: strategyId,
        symbol: symbol.toUpperCase(),
        exchange,
        interval,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
      })
      toast.success('Backtest started!')
      onBacktestStarted(response.id)
    } catch (error: any) {
      console.error('Failed to start backtest:', error)
      toast.error(error.response?.data?.detail || 'Failed to start backtest')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Strategy Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">
          <TrendingUp className="inline h-4 w-4 mr-2" />
          Strategy
        </label>
        {isLoadingStrategies ? (
          <div className="h-12 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
        ) : (
          <select
            value={strategyId}
            onChange={(e) => setStrategyId(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            required
          >
            <option value="">Select a strategy</option>
            {strategies.map((strategy) => (
              <option key={strategy.id} value={strategy.id}>
                {strategy.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Symbol and Exchange */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="symbol" className="block text-sm font-medium mb-2">
            Stock Symbol
          </label>
          <input
            id="symbol"
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary uppercase"
            placeholder="e.g., RELIANCE"
            required
          />
        </div>
        <div>
          <label htmlFor="exchange" className="block text-sm font-medium mb-2">
            Exchange
          </label>
          <select
            id="exchange"
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {exchanges.map((ex) => (
              <option key={ex.value} value={ex.value}>
                {ex.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="startDate" className="block text-sm font-medium mb-2">
            <Calendar className="inline h-4 w-4 mr-2" />
            Start Date
          </label>
          <input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            required
          />
        </div>
        <div>
          <label htmlFor="endDate" className="block text-sm font-medium mb-2">
            <Calendar className="inline h-4 w-4 mr-2" />
            End Date
          </label>
          <input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            required
          />
        </div>
      </div>

      {/* Quick date range buttons */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            setStartDate(format(subDays(new Date(), 30), 'yyyy-MM-dd'))
            setEndDate(format(new Date(), 'yyyy-MM-dd'))
          }}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          1 Month
        </button>
        <button
          type="button"
          onClick={() => {
            setStartDate(format(subDays(new Date(), 90), 'yyyy-MM-dd'))
            setEndDate(format(new Date(), 'yyyy-MM-dd'))
          }}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          3 Months
        </button>
        <button
          type="button"
          onClick={() => {
            setStartDate(format(subDays(new Date(), 180), 'yyyy-MM-dd'))
            setEndDate(format(new Date(), 'yyyy-MM-dd'))
          }}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          6 Months
        </button>
        <button
          type="button"
          onClick={() => {
            setStartDate(format(subDays(new Date(), 365), 'yyyy-MM-dd'))
            setEndDate(format(new Date(), 'yyyy-MM-dd'))
          }}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          1 Year
        </button>
        <button
          type="button"
          onClick={() => {
            setStartDate(format(subDays(new Date(), 730), 'yyyy-MM-dd'))
            setEndDate(format(new Date(), 'yyyy-MM-dd'))
          }}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          2 Years
        </button>
      </div>

      {/* Interval and Capital */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="interval" className="block text-sm font-medium mb-2">
            <Clock className="inline h-4 w-4 mr-2" />
            Data Interval
          </label>
          <select
            id="interval"
            value={interval}
            onChange={(e) => setInterval(e.target.value as BacktestInterval)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            {intervals.map((int) => (
              <option key={int.value} value={int.value}>
                {int.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="capital" className="block text-sm font-medium mb-2">
            <DollarSign className="inline h-4 w-4 mr-2" />
            Initial Capital
          </label>
          <input
            id="capital"
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            min={10000}
            step={10000}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            required
          />
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isSubmitting || isLoadingStrategies}
        className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
      >
        {isSubmitting ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            Starting Backtest...
          </>
        ) : (
          <>
            <Play className="h-5 w-5" />
            Run Backtest
          </>
        )}
      </button>
    </form>
  )
}
