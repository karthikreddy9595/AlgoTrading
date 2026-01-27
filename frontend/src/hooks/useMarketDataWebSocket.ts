'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { MarketQuote, CandleUpdate } from '@/types/market'

interface UseMarketDataWebSocketProps {
  symbols: string[]
  interval?: string
  enabled?: boolean
  onQuote?: (symbol: string, quote: MarketQuote) => void
  onCandle?: (symbol: string, candle: CandleUpdate) => void
}

interface MarketDataWebSocketState {
  isConnected: boolean
  error: string | null
  subscribedSymbols: string[]
  lastQuotes: Record<string, MarketQuote>
  lastCandles: Record<string, CandleUpdate>
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export function useMarketDataWebSocket({
  symbols,
  interval = '5min',
  enabled = true,
  onQuote,
  onCandle,
}: UseMarketDataWebSocketProps): MarketDataWebSocketState {
  const [state, setState] = useState<MarketDataWebSocketState>({
    isConnected: false,
    error: null,
    subscribedSymbols: [],
    lastQuotes: {},
    lastCandles: {},
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!enabled || symbols.length === 0) return

    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (!token) {
      setState((prev) => ({ ...prev, error: 'No authentication token' }))
      return
    }

    try {
      const ws = new WebSocket(`${WS_URL}/ws/market?token=${token}`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Market WebSocket connected')
        setState((prev) => ({ ...prev, isConnected: true, error: null }))

        // Subscribe to candles for all symbols
        ws.send(
          JSON.stringify({
            type: 'subscribe_candles',
            symbols,
            interval,
          })
        )

        // Start heartbeat to keep connection alive
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 30000) // Ping every 30 seconds
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Handle different message types
          switch (data.type) {
            case 'pong':
              // Heartbeat response
              break

            case 'candles_subscribed':
              setState((prev) => ({
                ...prev,
                subscribedSymbols: data.symbols || [],
              }))
              console.log('Subscribed to candles:', data.symbols)
              break

            case 'candles_unsubscribed':
              setState((prev) => ({
                ...prev,
                subscribedSymbols: prev.subscribedSymbols.filter(
                  (s) => !data.symbols.includes(s)
                ),
              }))
              break

            case 'quote':
              // Quote update
              if (data.symbol && data.data) {
                const quote: MarketQuote = {
                  symbol: data.symbol,
                  ltp: data.data.ltp,
                  open: data.data.open,
                  high: data.data.high,
                  low: data.data.low,
                  close: data.data.close,
                  volume: data.data.volume,
                  timestamp: data.data.timestamp,
                  bid: data.data.bid,
                  ask: data.data.ask,
                }

                setState((prev) => ({
                  ...prev,
                  lastQuotes: {
                    ...prev.lastQuotes,
                    [data.symbol]: quote,
                  },
                }))

                // Call callback if provided
                if (onQuote) {
                  onQuote(data.symbol, quote)
                }
              }
              break

            case 'candle':
              // Candle update (partial or completed)
              if (data.symbol && data.data) {
                const candle: CandleUpdate = {
                  timestamp: data.data.timestamp,
                  open: data.data.open,
                  high: data.data.high,
                  low: data.data.low,
                  close: data.data.close,
                  volume: data.data.volume,
                  is_partial: data.is_partial || false,
                }

                setState((prev) => ({
                  ...prev,
                  lastCandles: {
                    ...prev.lastCandles,
                    [data.symbol]: candle,
                  },
                }))

                // Call callback if provided
                if (onCandle) {
                  onCandle(data.symbol, candle)
                }
              }
              break

            case 'error':
              console.error('Market WebSocket error:', data.message)
              setState((prev) => ({ ...prev, error: data.message }))
              break

            default:
              console.log('Unknown message type:', data.type)
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setState((prev) => ({ ...prev, error: 'WebSocket connection error' }))
      }

      ws.onclose = () => {
        console.log('Market WebSocket disconnected')
        setState((prev) => ({ ...prev, isConnected: false }))
        wsRef.current = null

        // Clear heartbeat interval
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current)
          heartbeatIntervalRef.current = null
        }

        // Attempt reconnection after 5 seconds
        if (enabled) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...')
            connect()
          }, 5000)
        }
      }
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      setState((prev) => ({ ...prev, error: 'Failed to connect' }))
    }
  }, [symbols, interval, enabled, onQuote, onCandle])

  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Clear heartbeat interval
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }

    // Close WebSocket
    if (wsRef.current) {
      // Unsubscribe before closing
      if (wsRef.current.readyState === WebSocket.OPEN && symbols.length > 0) {
        wsRef.current.send(
          JSON.stringify({
            type: 'unsubscribe_candles',
            symbols,
            interval,
          })
        )
      }
      wsRef.current.close()
      wsRef.current = null
    }
  }, [symbols, interval])

  // Connect on mount or when dependencies change
  useEffect(() => {
    if (enabled && symbols.length > 0) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [symbols, interval, enabled, connect, disconnect])

  return state
}
