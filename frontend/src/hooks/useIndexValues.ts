'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { marketApi } from '@/lib/api'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export interface IndexValue {
  symbol: string
  display_name: string
  ltp: number | null
  change: number | null
  change_percent: number | null
  open?: number | null
  high?: number | null
  low?: number | null
  prev_close?: number | null
  timestamp?: string | null
}

export interface IndexValuesState {
  indices: Record<string, IndexValue>
  connected: boolean
  loading: boolean
  error: string | null
}

interface UseIndexValuesOptions {
  pollingInterval?: number // Fallback polling interval in ms (default: 5000)
  enabled?: boolean // Whether to enable the hook (default: true)
}

export function useIndexValues(options: UseIndexValuesOptions = {}) {
  const { pollingInterval = 5000, enabled = true } = options

  const [state, setState] = useState<IndexValuesState>({
    indices: {},
    connected: false,
    loading: true,
    error: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  // Fetch indices via REST API (initial load and fallback)
  const fetchIndices = useCallback(async () => {
    try {
      const data = await marketApi.getIndices()

      const indicesMap: Record<string, IndexValue> = {}
      for (const index of data.indices) {
        indicesMap[index.symbol] = index
      }

      setState((prev) => ({
        ...prev,
        indices: indicesMap,
        connected: data.connected,
        loading: false,
        error: data.message || null,
      }))
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: 'Failed to fetch index values',
      }))
    }
  }, [])

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (!enabled) return

    const token = localStorage.getItem('access_token')
    if (!token) {
      // No token, fall back to polling
      return
    }

    try {
      const ws = new WebSocket(`${WS_URL}/ws/market?token=${token}`)
      wsRef.current = ws

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0
        // Request current indices
        ws.send(JSON.stringify({ type: 'get_indices' }))
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          if (message.type === 'indices') {
            // Full indices update
            const indicesMap: Record<string, IndexValue> = {}
            for (const [key, value] of Object.entries(message.data)) {
              indicesMap[key] = value as IndexValue
            }
            setState((prev) => ({
              ...prev,
              indices: { ...prev.indices, ...indicesMap },
              connected: true,
              loading: false,
            }))
          } else if (message.type === 'index_update') {
            // Single index update
            setState((prev) => ({
              ...prev,
              indices: {
                ...prev.indices,
                [message.index]: message.data,
              },
              connected: true,
            }))
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onerror = () => {
        console.error('WebSocket error')
      }

      ws.onclose = () => {
        wsRef.current = null

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectAttemptsRef.current++

          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, delay)
        } else {
          // Max reconnect attempts reached, fall back to polling
          startPolling()
        }
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      startPolling()
    }
  }, [enabled])

  // Start REST API polling as fallback
  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return

    pollingIntervalRef.current = setInterval(() => {
      fetchIndices()
    }, pollingInterval)
  }, [fetchIndices, pollingInterval])

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }, [])

  // Cleanup
  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    stopPolling()
  }, [stopPolling])

  // Initialize
  useEffect(() => {
    if (!enabled) {
      cleanup()
      return
    }

    // Initial fetch
    fetchIndices()

    // Try WebSocket connection
    connectWebSocket()

    // Cleanup on unmount
    return cleanup
  }, [enabled, fetchIndices, connectWebSocket, cleanup])

  // Manual refresh function
  const refresh = useCallback(() => {
    fetchIndices()
  }, [fetchIndices])

  return {
    ...state,
    refresh,
  }
}
