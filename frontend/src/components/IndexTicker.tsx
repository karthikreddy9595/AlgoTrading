'use client'

import { useIndexValues, IndexValue } from '@/hooks/useIndexValues'
import { cn } from '@/lib/utils'

interface IndexItemProps {
  index: IndexValue | undefined
  loading?: boolean
}

function IndexItem({ index, loading }: IndexItemProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1">
        <span className="text-xs font-medium text-gray-500">--</span>
        <div className="h-3 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  if (!index) {
    return null
  }

  const hasValue = index.ltp !== null && index.ltp !== undefined
  const isPositive = (index.change_percent ?? 0) >= 0
  const changeColor = isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'

  return (
    <div className="flex items-center gap-1.5 px-2 py-1">
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
        {index.display_name}
      </span>
      {hasValue ? (
        <>
          <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">
            {index.ltp?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
          <span className={cn('text-xs font-medium', changeColor)}>
            {isPositive ? '\u25B2' : '\u25BC'}
            {Math.abs(index.change_percent ?? 0).toFixed(2)}%
          </span>
        </>
      ) : (
        <span className="text-xs text-gray-400">--</span>
      )}
    </div>
  )
}

export function IndexTicker() {
  const { indices, loading, connected, error } = useIndexValues()

  // Order of indices to display
  const indexOrder = ['NIFTY50', 'BANKNIFTY', 'SENSEX', 'BANKEX']

  // Placeholder indices when loading or no data
  const placeholderIndices: Record<string, { display_name: string }> = {
    NIFTY50: { display_name: 'NIFTY 50' },
    BANKNIFTY: { display_name: 'BANK NIFTY' },
    SENSEX: { display_name: 'SENSEX' },
    BANKEX: { display_name: 'BANKEX' },
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
      {indexOrder.map((key) => {
        const index = indices[key]
        const placeholder = placeholderIndices[key]

        if (loading && !index) {
          return (
            <IndexItem
              key={key}
              index={{ symbol: key, display_name: placeholder.display_name, ltp: null, change: null, change_percent: null }}
              loading
            />
          )
        }

        return (
          <IndexItem
            key={key}
            index={index || { symbol: key, display_name: placeholder.display_name, ltp: null, change: null, change_percent: null }}
          />
        )
      })}

      {/* Connection status indicator */}
      {!loading && !connected && (
        <div className="flex items-center gap-1 px-2">
          <div className="h-1.5 w-1.5 rounded-full bg-gray-400" />
          <span className="text-xs text-gray-400">Offline</span>
        </div>
      )}
    </div>
  )
}
