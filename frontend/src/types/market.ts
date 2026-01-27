// Market data and chart types

export interface IndicatorDataPoint {
  time: string // ISO format datetime
  value: number | null
}

export interface ChartIndicator {
  name: string // Display name: "Fast SMA (9)", "RSI (14)"
  type: string // Indicator type: "sma", "rsi", "ema", etc.
  pane: string // Chart pane: "main", "oscillator"
  color: string // Hex color for display
  data: IndicatorDataPoint[]
  params: Record<string, any> // e.g., {"period": 14, "overbought": 70}
}

export interface TradeMarker {
  time: string // ISO datetime
  price: number
  type: 'entry' | 'exit'
  side: 'buy' | 'sell'
  quantity: number
  pnl?: number | null
  pnl_percent?: number | null
  order_id: string
  trade_id?: string | null
}

export interface HistoricalCandle {
  timestamp: string // ISO datetime
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ChartDataResponse {
  symbol: string
  exchange: string
  interval: string
  strategy_name: string
  strategy_slug: string
  candles: HistoricalCandle[]
  indicators: ChartIndicator[]
  trades: TradeMarker[]
  message?: string | null
}

export interface MarketQuote {
  symbol: string
  ltp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: string
  bid: number
  ask: number
}

export interface CandleUpdate {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  is_partial: boolean
}
