'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import {
  ArrowLeft,
  FlaskConical,
  Loader2,
  Calendar,
  Clock,
  DollarSign,
  AlertCircle,
  Settings2,
  TrendingUp,
} from 'lucide-react'
import { backtestApi, strategyApi } from '@/lib/api'
import { Backtest, BacktestResult } from '@/types/backtest'
import { formatCurrency, cn } from '@/lib/utils'
import { format, parseISO } from 'date-fns'
import { toast } from 'sonner'

// Helper to safely parse date strings
const safeFormatDate = (dateStr: string | undefined, formatStr: string): string => {
  if (!dateStr) return 'N/A'
  try {
    // Try parsing as ISO date first, then as regular Date
    const date = dateStr.includes('T') ? parseISO(dateStr) : new Date(dateStr + 'T00:00:00')
    return format(date, formatStr)
  } catch {
    return dateStr
  }
}
import { BacktestResultsMetrics } from '../components/BacktestResultsMetrics'
import { BacktestChart } from '../components/BacktestChart'
import { BacktestTradesList } from '../components/BacktestTradesList'
import { OptimizationModal } from '../components/OptimizationModal'
import { OptimizationProgress } from '../components/OptimizationProgress'
import { OptimizationResults } from '../components/OptimizationResults'
import { SubscribeModal } from '../components/SubscribeModal'

type TabType = 'overview' | 'trades' | 'chart' | 'optimization'
type OptimizationState = 'idle' | 'modal' | 'running' | 'completed'

export default function BacktestResultsPage() {
  const router = useRouter()
  const params = useParams()
  const backtestId = params.id as string

  const [backtest, setBacktest] = useState<Backtest | null>(null)
  const [results, setResults] = useState<BacktestResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  // Optimization state
  const [optimizationState, setOptimizationState] = useState<OptimizationState>('idle')
  const [optimizationId, setOptimizationId] = useState<string | null>(null)

  // Subscribe state
  const [showSubscribeModal, setShowSubscribeModal] = useState(false)
  const [strategy, setStrategy] = useState<any>(null)

  useEffect(() => {
    fetchData()
  }, [backtestId])

  const fetchData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Fetch full backtest details
      const backtestData = await backtestApi.get(backtestId)
      setBacktest(backtestData)

      // Fetch strategy details
      if (backtestData.strategy_id) {
        const strategyData = await strategyApi.get(backtestData.strategy_id)
        setStrategy(strategyData)
      }

      // If completed, fetch results
      if (backtestData.status === 'completed') {
        const resultsData = await backtestApi.getResults(backtestId)
        setResults(resultsData)
      } else if (backtestData.status === 'failed') {
        setError(backtestData.error_message || 'Backtest failed')
      } else if (backtestData.status === 'running' || backtestData.status === 'pending') {
        // Redirect back to main page to show progress
        router.push('/dashboard/backtest')
        return
      }
    } catch (err: any) {
      console.error('Failed to fetch backtest data:', err)
      setError(err.response?.data?.detail || 'Failed to load backtest data')
    } finally {
      setIsLoading(false)
    }
  }

  const handleOptimizeClick = () => {
    setOptimizationState('modal')
  }

  const handleOptimizationStarted = (id: string) => {
    setOptimizationId(id)
    setOptimizationState('running')
  }

  const handleOptimizationCompleted = () => {
    setOptimizationState('completed')
    setActiveTab('optimization')
  }

  const handleOptimizationCancelled = () => {
    setOptimizationState('idle')
    setOptimizationId(null)
  }

  const handleSubscribeSuccess = (subscriptionId: string) => {
    toast.success('Successfully subscribed to strategy!')
    setShowSubscribeModal(false)
    // Redirect to strategies page to see the live strategy
    router.push('/dashboard/strategies')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !backtest) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => router.push('/dashboard/backtest')}
          className="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Backtest
        </button>

        <div className="flex flex-col items-center justify-center h-64 text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <h2 className="text-xl font-semibold mb-2">Error Loading Backtest</h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">{error || 'Backtest not found'}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  const tabs: TabType[] = optimizationState === 'completed'
    ? ['overview', 'chart', 'trades', 'optimization']
    : ['overview', 'chart', 'trades']

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => router.push('/dashboard/backtest')}
        className="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Backtest
      </button>

      {/* Header */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <FlaskConical className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">{backtest.symbol}</h1>
                <span className="text-sm text-gray-500">{backtest.exchange}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Subscribe Button */}
            <button
              onClick={() => setShowSubscribeModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <TrendingUp className="h-4 w-4" />
              Subscribe
            </button>
            {/* Optimize Button */}
            <button
              onClick={handleOptimizeClick}
              disabled={optimizationState === 'running'}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Settings2 className="h-4 w-4" />
              Optimize
            </button>
            <span className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full text-sm font-medium">
              Completed
            </span>
          </div>
        </div>

        {/* Backtest Details */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500 dark:text-gray-400">Period:</span>
            <span className="font-medium">
              {safeFormatDate(backtest.start_date, 'MMM d, yyyy')} -{' '}
              {safeFormatDate(backtest.end_date, 'MMM d, yyyy')}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500 dark:text-gray-400">Interval:</span>
            <span className="font-medium">{backtest.interval}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <DollarSign className="h-4 w-4 text-gray-400" />
            <span className="text-gray-500 dark:text-gray-400">Initial Capital:</span>
            <span className="font-medium">{formatCurrency(backtest.initial_capital)}</span>
          </div>
          {backtest.completed_at && (
            <div className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-gray-400" />
              <span className="text-gray-500 dark:text-gray-400">Completed:</span>
              <span className="font-medium">
                {safeFormatDate(backtest.completed_at, 'MMM d, yyyy HH:mm')}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Optimization Progress (shown when running) */}
      {optimizationState === 'running' && optimizationId && (
        <OptimizationProgress
          optimizationId={optimizationId}
          onCompleted={handleOptimizationCompleted}
          onCancelled={handleOptimizationCancelled}
        />
      )}

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-800">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px capitalize',
              activeTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && results && (
        <BacktestResultsMetrics results={results} initialCapital={backtest.initial_capital} />
      )}

      {activeTab === 'chart' && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <BacktestChart backtestId={backtestId} symbol={backtest.symbol} />
        </div>
      )}

      {activeTab === 'trades' && (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
          <h2 className="text-lg font-semibold mb-4">Trade History</h2>
          <BacktestTradesList backtestId={backtestId} />
        </div>
      )}

      {activeTab === 'optimization' && optimizationId && (
        <OptimizationResults
          optimizationId={optimizationId}
          initialCapital={backtest.initial_capital}
        />
      )}

      {/* Optimization Modal */}
      {optimizationState === 'modal' && (
        <OptimizationModal
          backtestId={backtestId}
          strategyId={backtest.strategy_id}
          onClose={() => setOptimizationState('idle')}
          onStarted={handleOptimizationStarted}
        />
      )}

      {/* Subscribe Modal */}
      {showSubscribeModal && backtest && strategy && (
        <SubscribeModal
          backtestId={backtestId}
          strategyName={strategy.name}
          symbol={backtest.symbol}
          minCapital={strategy.min_capital || 10000}
          onClose={() => setShowSubscribeModal(false)}
          onSuccess={handleSubscribeSuccess}
          hasOptimization={optimizationState === 'completed'}
        />
      )}
    </div>
  )
}
