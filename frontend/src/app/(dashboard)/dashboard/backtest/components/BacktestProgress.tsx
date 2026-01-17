'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { backtestApi } from '@/lib/api'
import { BacktestProgress as BacktestProgressType, BacktestStatus } from '@/types/backtest'
import { cn } from '@/lib/utils'

interface BacktestProgressProps {
  backtestId: string
  onComplete?: () => void
  onError?: (error: string) => void
}

export function BacktestProgress({ backtestId, onComplete, onError }: BacktestProgressProps) {
  const router = useRouter()
  const [progress, setProgress] = useState<BacktestProgressType | null>(null)
  const [isPolling, setIsPolling] = useState(true)

  const fetchProgress = useCallback(async () => {
    try {
      const data = await backtestApi.getStatus(backtestId)
      setProgress(data)

      if (data.status === 'completed') {
        setIsPolling(false)
        onComplete?.()
        // Navigate to results page after a short delay
        setTimeout(() => {
          router.push(`/dashboard/backtest/${backtestId}`)
        }, 1000)
      } else if (data.status === 'failed' || data.status === 'cancelled') {
        setIsPolling(false)
        onError?.(data.error_message || 'Backtest failed')
      }
    } catch (error) {
      console.error('Failed to fetch progress:', error)
    }
  }, [backtestId, onComplete, onError, router])

  useEffect(() => {
    if (!isPolling) return

    fetchProgress()
    const interval = setInterval(fetchProgress, 1000)

    return () => clearInterval(interval)
  }, [fetchProgress, isPolling])

  const getStatusIcon = (status: BacktestStatus) => {
    switch (status) {
      case 'pending':
        return <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
      case 'running':
        return <Loader2 className="h-6 w-6 animate-spin text-primary" />
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-500" />
      case 'failed':
        return <XCircle className="h-6 w-6 text-red-500" />
      case 'cancelled':
        return <AlertCircle className="h-6 w-6 text-yellow-500" />
      default:
        return <Loader2 className="h-6 w-6 animate-spin" />
    }
  }

  const getStatusText = (status: BacktestStatus) => {
    switch (status) {
      case 'pending':
        return 'Initializing backtest...'
      case 'running':
        return 'Running backtest...'
      case 'completed':
        return 'Backtest completed!'
      case 'failed':
        return 'Backtest failed'
      case 'cancelled':
        return 'Backtest cancelled'
      default:
        return 'Processing...'
    }
  }

  const getProgressColor = (status: BacktestStatus) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      case 'cancelled':
        return 'bg-yellow-500'
      default:
        return 'bg-primary'
    }
  }

  if (!progress) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center gap-4 mb-4">
        {getStatusIcon(progress.status)}
        <div>
          <h3 className="font-semibold">{getStatusText(progress.status)}</h3>
          {progress.message && (
            <p className="text-sm text-gray-500 dark:text-gray-400">{progress.message}</p>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full transition-all duration-500 ease-out rounded-full',
              getProgressColor(progress.status)
            )}
            style={{ width: `${progress.progress}%` }}
          />
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-200 drop-shadow-sm">
            {progress.progress}%
          </span>
        </div>
      </div>

      {/* Error Message */}
      {progress.error_message && (
        <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">{progress.error_message}</p>
        </div>
      )}

      {/* Action Buttons */}
      {progress.status === 'completed' && (
        <div className="mt-4">
          <button
            onClick={() => router.push(`/dashboard/backtest/${backtestId}`)}
            className="w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            View Results
          </button>
        </div>
      )}

      {(progress.status === 'pending' || progress.status === 'running') && (
        <div className="mt-4">
          <button
            onClick={async () => {
              try {
                await backtestApi.delete(backtestId)
                setIsPolling(false)
                onError?.('Backtest cancelled')
              } catch (error) {
                console.error('Failed to cancel backtest:', error)
              }
            }}
            className="w-full px-4 py-2 border border-red-500 text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            Cancel Backtest
          </button>
        </div>
      )}
    </div>
  )
}
