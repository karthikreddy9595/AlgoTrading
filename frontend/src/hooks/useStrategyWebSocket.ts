'use client'

import { useEffect, useState, useCallback, useRef } from 'react'

interface StrategyEvent {
  type: string
  timestamp: string
  data: Record<string, unknown>
}

interface UseStrategyWebSocketOptions {
  subscriptionId: string | null
  enabled?: boolean
}

interface StrategyWebSocketState {
  status: string
  pnl: number
  todayPnl: number
  events: StrategyEvent[]
  isConnected: boolean
  error: string | null
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export function useStrategyWebSocket({ subscriptionId, enabled = true }: UseStrategyWebSocketOptions): StrategyWebSocketState {
  const [state, setState] = useState<StrategyWebSocketState>({
    status: 'unknown',
    pnl: 0,
    todayPnl: 0,
    events: [],
    isConnected: false,
    error: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!subscriptionId || !enabled) return

    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (!token) {
      setState(prev => ({ ...prev, error: 'No authentication token' }))
      return
    }

    try {
      const ws = new WebSocket(`${WS_URL}/ws/portfolio?token=${token}`)
      wsRef.current = ws

      ws.onopen = () => {
        setState(prev => ({ ...prev, isConnected: true, error: null }))

        // Subscribe to strategy updates
        ws.send(JSON.stringify({
          type: 'subscribe_strategy',
          subscription_id: subscriptionId,
        }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Handle different message types
          if (data.type === 'strategy_status' && data.subscription_id === subscriptionId) {
            setState(prev => ({
              ...prev,
              status: data.status,
            }))
          }

          if (data.type === 'pnl_update' && data.subscription_id === subscriptionId) {
            setState(prev => ({
              ...prev,
              pnl: data.total_pnl || prev.pnl,
              todayPnl: data.today_pnl || prev.todayPnl,
            }))
          }

          if (data.type === 'order_update' && data.subscription_id === subscriptionId) {
            const event: StrategyEvent = {
              type: 'order',
              timestamp: data.timestamp || new Date().toISOString(),
              data: data,
            }
            setState(prev => ({
              ...prev,
              events: [event, ...prev.events].slice(0, 50),
            }))
          }

          if (data.type === 'position_update' && data.subscription_id === subscriptionId) {
            const event: StrategyEvent = {
              type: 'position',
              timestamp: data.timestamp || new Date().toISOString(),
              data: data,
            }
            setState(prev => ({
              ...prev,
              events: [event, ...prev.events].slice(0, 50),
            }))
          }

          if (data.type === 'error') {
            setState(prev => ({ ...prev, error: data.message }))
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setState(prev => ({ ...prev, error: 'WebSocket connection error' }))
      }

      ws.onclose = () => {
        setState(prev => ({ ...prev, isConnected: false }))
        wsRef.current = null

        // Attempt reconnection after 5 seconds
        if (enabled) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, 5000)
        }
      }
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      setState(prev => ({ ...prev, error: 'Failed to connect' }))
    }
  }, [subscriptionId, enabled])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      // Unsubscribe before closing
      if (subscriptionId && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'unsubscribe_strategy',
          subscription_id: subscriptionId,
        }))
      }
      wsRef.current.close()
      wsRef.current = null
    }
  }, [subscriptionId])

  useEffect(() => {
    if (enabled && subscriptionId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [subscriptionId, enabled, connect, disconnect])

  return state
}

// Hook for subscribing to all user's strategies
export function useAllStrategiesWebSocket(enabled = true) {
  const [strategies, setStrategies] = useState<Record<string, {
    status: string
    pnl: number
    todayPnl: number
  }>>({})
  const [isConnected, setIsConnected] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!enabled) return

    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (!token) return

    const ws = new WebSocket(`${WS_URL}/ws/portfolio?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      // Subscribe to all strategy updates
      ws.send(JSON.stringify({ type: 'subscribe_all_strategies' }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'strategy_status' && data.subscription_id) {
          setStrategies(prev => ({
            ...prev,
            [data.subscription_id]: {
              ...prev[data.subscription_id],
              status: data.status,
            },
          }))
        }

        if (data.type === 'pnl_update' && data.subscription_id) {
          setStrategies(prev => ({
            ...prev,
            [data.subscription_id]: {
              ...prev[data.subscription_id],
              pnl: data.total_pnl || 0,
              todayPnl: data.today_pnl || 0,
            },
          }))
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      wsRef.current = null
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [enabled])

  return { strategies, isConnected }
}
