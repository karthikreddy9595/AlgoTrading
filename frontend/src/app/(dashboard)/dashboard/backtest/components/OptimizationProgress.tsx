'use client'

import { useState, useEffect } from 'react'
import { Loader2, CheckCircle, XCircle, AlertCircle, X } from 'lucide-react'
import { optimizationApi } from '@/lib/api'
import { OptimizationProgress as OptimizationProgressType } from '@/types/optimization'
import { toast } from 'sonner'

interface OptimizationProgressProps {
  optimizationId: string
  onCompleted: () => void
  onCancelled: () => void
}

export function OptimizationProgress({
  optimizationId,
  onCompleted,
  onCancelled,
}: OptimizationProgressProps) {
  const [progress, setProgress] = useState<OptimizationProgressType | null>(null)
  const [isCancelling, setIsCancelling] = useState(false)

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const status = await optimizationApi.getStatus(optimizationId)
        setProgress(status)

        if (status.status === 'completed') {
          onCompleted()
        } else if (status.status === 'failed' || status.status === 'cancelled') {
          if (status.status === 'failed') {
            toast.error(status.error_message || 'Optimization failed')
          }
          onCancelled()
        }
      } catch (err) {
        console.error('Failed to fetch optimization status:', err)
      }
    }

    // Initial fetch
    pollStatus()

    // Poll every 1 second
    const interval = setInterval(pollStatus, 1000)

    return () => clearInterval(interval)
  }, [optimizationId, onCompleted, onCancelled])

  const handleCancel = async () => {
    setIsCancelling(true)
    try {
      await optimizationApi.delete(optimizationId)
      toast.info('Optimization cancelled')
      onCancelled()
    } catch (err: any) {
      console.error('Failed to cancel optimization:', err)
      toast.error(err.response?.data?.detail || 'Failed to cancel optimization')
    } finally {
      setIsCancelling(false)
    }
  }

  const getStatusIcon = () => {
    if (!progress) return <Loader2 className="h-6 w-6 animate-spin text-primary" />

    switch (progress.status) {
      case 'pending':
        return <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
      case 'running':
        return <Loader2 className="h-6 w-6 animate-spin text-primary" />
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-500" />
      case 'failed':
        return <XCircle className="h-6 w-6 text-red-500" />
      case 'cancelled':
        return <AlertCircle className="h-6 w-6 text-gray-500" />
      default:
        return <Loader2 className="h-6 w-6 animate-spin text-primary" />
    }
  }

  const getStatusText = () => {
    if (!progress) return 'Loading...'

    switch (progress.status) {
      case 'pending':
        return 'Preparing optimization...'
      case 'running':
        return `Testing parameter combinations (${progress.completed_samples}/${progress.total_samples})`
      case 'completed':
        return 'Optimization completed!'
      case 'failed':
        return 'Optimization failed'
      case 'cancelled':
        return 'Optimization cancelled'
      default:
        return 'Unknown status'
    }
  }

  const progressPercent = progress?.progress || 0

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">Optimization Progress</h3>
        {progress?.status === 'running' && (
          <button
            onClick={handleCancel}
            disabled={isCancelling}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
          >
            {isCancelling ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <X className="h-4 w-4" />
            )}
            Cancel
          </button>
        )}
      </div>

      <div className="flex flex-col items-center justify-center py-8">
        {/* Status Icon */}
        <div className="mb-4">{getStatusIcon()}</div>

        {/* Status Text */}
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">{getStatusText()}</p>

        {/* Progress Bar */}
        {progress?.status === 'running' && (
          <div className="w-full max-w-md">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{progress.completed_samples} completed</span>
              <span>{progressPercent}%</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300 rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* Error Message */}
        {progress?.error_message && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
            {progress.error_message}
          </div>
        )}
      </div>
    </div>
  )
}
