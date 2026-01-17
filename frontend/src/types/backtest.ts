// Backtest Types

export type BacktestStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export type BacktestInterval = '1min' | '5min' | '15min' | '30min' | '1hour' | '1day'

export interface BacktestCreate {
  strategy_id: string
  symbol: string
  exchange?: string
  interval?: BacktestInterval
  start_date: string
  end_date: string
  initial_capital: number
  config?: Record<string, unknown>
}

export interface Backtest {
  id: string
  user_id: string
  strategy_id: string
  status: BacktestStatus
  symbol: string
  exchange: string
  interval: string
  start_date: string
  end_date: string
  initial_capital: number
  config?: Record<string, unknown>
  progress: number
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface BacktestListItem {
  id: string
  strategy_id: string
  status: BacktestStatus
  symbol: string
  exchange: string
  interval: string
  start_date: string
  end_date: string
  initial_capital: number
  progress: number
  created_at: string
  completed_at?: string
  total_return_percent?: number
  total_trades?: number
  error_message?: string
}

export interface BacktestProgress {
  id: string
  status: BacktestStatus
  progress: number
  message?: string
  error_message?: string
  started_at?: string
  completed_at?: string
}

export interface BacktestResult {
  id: string
  backtest_id: string
  total_return?: number
  total_return_percent?: number
  cagr?: number
  sharpe_ratio?: number
  sortino_ratio?: number
  calmar_ratio?: number
  max_drawdown?: number
  avg_drawdown?: number
  win_rate?: number
  profit_factor?: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  avg_trade_duration?: number
  final_capital?: number
  max_capital?: number
  created_at: string
}

export interface BacktestTrade {
  id: string
  backtest_id: string
  signal: 'BUY' | 'SELL' | 'EXIT_LONG' | 'EXIT_SHORT'
  entry_price: number
  exit_price?: number
  quantity: number
  entry_time: string
  exit_time?: string
  pnl?: number
  pnl_percent?: number
  reason?: string
  is_open: boolean
}

export interface BacktestTradeList {
  trades: BacktestTrade[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CandleData {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface ChartMarker {
  time: number
  position: 'aboveBar' | 'belowBar'
  color: string
  shape: 'arrowUp' | 'arrowDown' | 'circle'
  text: string
}

export interface EquityCurvePoint {
  time: number
  value: number
}

export interface IndicatorDataPoint {
  time: number
  value: number | null
}

export interface IndicatorSeries {
  name: string
  data: IndicatorDataPoint[]
  type: string  // "line", "histogram", etc.
  pane: string  // "main" for price overlays, "rsi", "macd", etc. for separate panes
  color?: string
  signal_line?: IndicatorDataPoint[]
  histogram?: IndicatorDataPoint[]
}

export interface BacktestChartData {
  candles: CandleData[]
  markers: ChartMarker[]
  equity_curve: EquityCurvePoint[]
  indicators?: IndicatorSeries[]
}

export interface BacktestProgressUpdate {
  backtest_id: string
  status: BacktestStatus
  progress: number
  message: string
  current_date?: string
  trades_count?: number
}
