'use client'

import { useState, useEffect } from 'react'
import { FlaskConical, Plus, History, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BacktestForm } from './components/BacktestForm'
import { BacktestProgress } from './components/BacktestProgress'
import { BacktestHistory } from './components/BacktestHistory'
import { userApi } from '@/lib/api'
import { toast } from 'sonner'
import Link from 'next/link'

type TabType = 'new' | 'history'

export default function BacktestPage() {
  const [activeTab, setActiveTab] = useState<TabType>('new')
  const [runningBacktestId, setRunningBacktestId] = useState<string | null>(null)
  const [hasBrokerConnection, setHasBrokerConnection] = useState<boolean | null>(null)

  useEffect(() => {
    checkBrokerConnection()
  }, [])

  const checkBrokerConnection = async () => {
    try {
      const connections = await userApi.getBrokerConnections()
      // Check if user has any active broker connection
      const hasActive = connections?.some((c: any) => c.is_active) ?? false
      setHasBrokerConnection(hasActive)
    } catch (error) {
      console.error('Failed to check broker connection:', error)
      setHasBrokerConnection(false)
    }
  }

  const handleBacktestStarted = (backtestId: string) => {
    setRunningBacktestId(backtestId)
  }

  const handleBacktestComplete = () => {
    setRunningBacktestId(null)
  }

  const handleBacktestError = (error: string) => {
    setRunningBacktestId(null)
    toast.error(error || 'Backtest failed')
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <FlaskConical className="h-8 w-8 text-primary" />
          <h1 className="text-2xl font-bold">Backtest</h1>
        </div>
        <p className="text-gray-500 dark:text-gray-400">
          Test your trading strategies on historical data
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-800">
        <button
          onClick={() => setActiveTab('new')}
          className={cn(
            'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px',
            activeTab === 'new'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          )}
        >
          <Plus className="h-4 w-4" />
          New Backtest
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={cn(
            'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px',
            activeTab === 'history'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
          )}
        >
          <History className="h-4 w-4" />
          History
        </button>
      </div>

      {/* Broker Connection Warning */}
      {hasBrokerConnection === false && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-yellow-800 dark:text-yellow-200">
                Broker Connection Required
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                Backtesting requires historical market data from your broker. Please connect your broker account first.
              </p>
              <Link
                href="/dashboard/broker"
                className="inline-flex items-center gap-1 mt-2 text-sm font-medium text-yellow-800 dark:text-yellow-200 hover:underline"
              >
                Connect Broker
                <span aria-hidden="true">&rarr;</span>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Tab Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {activeTab === 'new' && (
          <>
            {/* Backtest Form */}
            <div className="lg:col-span-2">
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-lg font-semibold mb-6">Configure Backtest</h2>
                {runningBacktestId ? (
                  <BacktestProgress
                    backtestId={runningBacktestId}
                    onComplete={handleBacktestComplete}
                    onError={handleBacktestError}
                  />
                ) : (
                  <BacktestForm onBacktestStarted={handleBacktestStarted} />
                )}
              </div>
            </div>

            {/* Quick Tips */}
            <div className="lg:col-span-1">
              <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-lg font-semibold mb-4">Tips</h2>
                <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                      1
                    </span>
                    <span>
                      Choose a strategy that matches your trading style and risk tolerance.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                      2
                    </span>
                    <span>
                      Use longer date ranges (1+ year) for more reliable results.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                      3
                    </span>
                    <span>
                      Smaller intervals (1min, 5min) require more data and take longer to process.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                      4
                    </span>
                    <span>
                      Pay attention to drawdown and Sharpe ratio, not just returns.
                    </span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                      5
                    </span>
                    <span>
                      Past performance does not guarantee future results.
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </>
        )}

        {activeTab === 'history' && (
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
              <BacktestHistory />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
