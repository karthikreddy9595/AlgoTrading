'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Loader2, Circle } from 'lucide-react'
import { marketApi } from '@/lib/api'
import { ChartDataResponse, ChartIndicator, CandleUpdate } from '@/types/market'
import { cn } from '@/lib/utils'
import { useMarketDataWebSocket } from '@/hooks/useMarketDataWebSocket'

interface StrategyChartProps {
  symbol: string
  subscriptionId: string
  fromDate?: Date
  toDate?: Date
  height?: number
  showVolume?: boolean
  enableRealtime?: boolean
}

export function StrategyChart({
  symbol,
  subscriptionId,
  fromDate,
  toDate,
  height = 400,
  showVolume = true,
  enableRealtime = true,
}: StrategyChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const oscillatorChartRef = useRef<HTMLDivElement>(null)
  const mainChartRef = useRef<any>(null)
  const oscillatorChartInstanceRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const [chartData, setChartData] = useState<ChartDataResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [chartLib, setChartLib] = useState<any>(null)

  // Handle real-time candle updates
  const handleCandleUpdate = useCallback((symbol: string, candle: CandleUpdate) => {
    if (!candlestickSeriesRef.current || !chartData) return

    try {
      const candleTime = new Date(candle.timestamp).getTime() / 1000
      const newCandle = {
        time: candleTime,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }

      // Update the candle series
      if (candle.is_partial) {
        // Update current candle
        candlestickSeriesRef.current.update(newCandle)
      } else {
        // Add completed candle
        candlestickSeriesRef.current.update(newCandle)
      }
    } catch (err) {
      console.error('Failed to update candle:', err)
    }
  }, [chartData])

  // WebSocket for real-time updates
  const wsState = useMarketDataWebSocket({
    symbols: enableRealtime ? [symbol] : [],
    interval: chartData?.interval || '5min',
    enabled: enableRealtime && !!chartData,
    onCandle: handleCandleUpdate,
  })

  // Load chart library dynamically
  useEffect(() => {
    const loadChartLibrary = async () => {
      try {
        const lib = await import('lightweight-charts')
        setChartLib(lib)
      } catch (err) {
        console.error('Failed to load chart library:', err)
        setError('Failed to load chart library. Please refresh the page.')
      }
    }
    loadChartLibrary()
  }, [])

  // Fetch chart data
  useEffect(() => {
    // Don't fetch if symbol or subscriptionId is missing
    if (!symbol || !subscriptionId) {
      setIsLoading(false)
      setError('Symbol and subscription ID are required')
      return
    }

    const fetchData = async () => {
      setIsLoading(true)
      setError(null)
      try {
        // Parse symbol format: "EXCHANGE:SYMBOL" or just "SYMBOL"
        let parsedSymbol = symbol.trim()
        let exchange = 'NSE' // default exchange

        if (parsedSymbol.includes(':')) {
          const parts = parsedSymbol.split(':')
          exchange = parts[0]
          parsedSymbol = parts[1]
        }

        // Validate parsed symbol is not empty
        if (!parsedSymbol) {
          setError('Invalid symbol format')
          setIsLoading(false)
          return
        }

        const data = await marketApi.getChartData({
          symbol: parsedSymbol,
          subscription_id: subscriptionId,
          exchange: exchange,
          from_date: fromDate,
          to_date: toDate,
        })
        setChartData(data)
      } catch (err: any) {
        console.error('Failed to fetch chart data:', err)
        setError(err.response?.data?.detail || 'Failed to load chart data')
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [symbol, subscriptionId, fromDate, toDate])

  // Create/update chart
  useEffect(() => {
    if (!chartLib || !chartData || !chartContainerRef.current) return

    // Clean up existing charts
    if (mainChartRef.current) {
      mainChartRef.current.remove()
      mainChartRef.current = null
    }
    if (oscillatorChartInstanceRef.current) {
      oscillatorChartInstanceRef.current.remove()
      oscillatorChartInstanceRef.current = null
    }

    const { createChart, ColorType, CrosshairMode } = chartLib

    // Create main price chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: 'rgba(55, 65, 81, 0.3)' },
        horzLines: { color: 'rgba(55, 65, 81, 0.3)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: 'rgba(55, 65, 81, 0.5)',
      },
      timeScale: {
        borderColor: 'rgba(55, 65, 81, 0.5)',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        vertTouchDrag: false,
      },
      height,
    })

    // Add candlestick series
    const candleOptions = {
      upColor: '#10B981',
      downColor: '#EF4444',
      borderDownColor: '#EF4444',
      borderUpColor: '#10B981',
      wickDownColor: '#EF4444',
      wickUpColor: '#10B981',
    }

    let candlestickSeries: any
    try {
      // Try v5 API
      candlestickSeries = chart.addSeries(chartLib.CandlestickSeries, candleOptions)
    } catch {
      // Fallback to v4 API
      candlestickSeries = (chart as any).addCandlestickSeries(candleOptions)
    }

    // Set candle data
    const candleData = chartData.candles.map((candle) => ({
      time: new Date(candle.timestamp).getTime() / 1000,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }))
    candlestickSeries.setData(candleData)

    // Store reference for real-time updates
    candlestickSeriesRef.current = candlestickSeries

    // Add trade markers
    if (chartData.trades && chartData.trades.length > 0) {
      const markers = chartData.trades.map((trade) => {
        const isEntry = trade.type === 'entry'
        const isBuy = trade.side === 'buy'

        return {
          time: new Date(trade.time).getTime() / 1000,
          position: isEntry
            ? isBuy
              ? 'belowBar'
              : 'aboveBar'
            : isBuy
            ? 'belowBar'
            : 'aboveBar',
          color: isEntry
            ? isBuy
              ? '#10B981'
              : '#EF4444'
            : isBuy
            ? '#F59E0B'
            : '#F59E0B',
          shape: isEntry ? 'arrowUp' : 'arrowDown',
          text: isEntry
            ? `${isBuy ? 'BUY' : 'SELL'} ${trade.quantity}`
            : `EXIT ${trade.pnl ? (trade.pnl > 0 ? '+' : '') + trade.pnl.toFixed(2) : ''}`,
        } as any
      })
      candlestickSeries.setMarkers(markers)
    }

    // Add SMA indicators on main pane
    const mainPaneIndicators = chartData.indicators.filter((ind) => ind.pane === 'main')
    mainPaneIndicators.forEach((indicator) => {
      const lineOptions = {
        color: indicator.color,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        title: indicator.name,
      }

      let lineSeries: any
      try {
        lineSeries = chart.addSeries(chartLib.LineSeries, lineOptions)
      } catch {
        lineSeries = (chart as any).addLineSeries(lineOptions)
      }

      const lineData = indicator.data
        .filter((d) => d.value !== null)
        .map((d) => ({
          time: new Date(d.time).getTime() / 1000,
          value: d.value,
        }))
      lineSeries.setData(lineData)
    })

    // Add volume series if enabled
    if (showVolume && chartData.candles.some((c) => c.volume > 0)) {
      const volumeOptions = {
        color: '#6366F1',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      }

      let volumeSeries: any
      try {
        volumeSeries = chart.addSeries(chartLib.HistogramSeries, volumeOptions)
      } catch {
        volumeSeries = (chart as any).addHistogramSeries(volumeOptions)
      }

      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      })

      const volumeData = chartData.candles.map((candle) => ({
        time: new Date(candle.timestamp).getTime() / 1000,
        value: candle.volume,
        color:
          candle.close >= candle.open
            ? 'rgba(16, 185, 129, 0.3)'
            : 'rgba(239, 68, 68, 0.3)',
      }))
      volumeSeries.setData(volumeData)
    }

    chart.timeScale().fitContent()
    mainChartRef.current = chart

    // Create oscillator chart (RSI) if indicators exist
    const oscillatorIndicators = chartData.indicators.filter(
      (ind) => ind.pane === 'oscillator'
    )
    if (oscillatorIndicators.length > 0 && oscillatorChartRef.current) {
      const oscillatorChart = createChart(oscillatorChartRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#9CA3AF',
        },
        grid: {
          vertLines: { color: 'rgba(55, 65, 81, 0.3)' },
          horzLines: { color: 'rgba(55, 65, 81, 0.3)' },
        },
        rightPriceScale: {
          borderColor: 'rgba(55, 65, 81, 0.5)',
        },
        timeScale: {
          borderColor: 'rgba(55, 65, 81, 0.5)',
          visible: false,
        },
        height: 150,
      })

      oscillatorIndicators.forEach((indicator) => {
        const lineOptions = {
          color: indicator.color,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
        }

        let lineSeries: any
        try {
          lineSeries = oscillatorChart.addSeries(chartLib.LineSeries, lineOptions)
        } catch {
          lineSeries = (oscillatorChart as any).addLineSeries(lineOptions)
        }

        const lineData = indicator.data
          .filter((d) => d.value !== null)
          .map((d) => ({
            time: new Date(d.time).getTime() / 1000,
            value: d.value,
          }))
        lineSeries.setData(lineData)

        // Add reference lines for RSI if it's an RSI indicator
        if (indicator.type === 'rsi') {
          oscillatorChart.priceScale('right').applyOptions({
            scaleMargins: { top: 0.1, bottom: 0.1 },
          })
        }
      })

      oscillatorChart.timeScale().fitContent()
      oscillatorChartInstanceRef.current = oscillatorChart
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && mainChartRef.current) {
        mainChartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
      if (oscillatorChartRef.current && oscillatorChartInstanceRef.current) {
        oscillatorChartInstanceRef.current.applyOptions({
          width: oscillatorChartRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (mainChartRef.current) {
        mainChartRef.current.remove()
        mainChartRef.current = null
      }
      if (oscillatorChartInstanceRef.current) {
        oscillatorChartInstanceRef.current.remove()
        oscillatorChartInstanceRef.current = null
      }
      candlestickSeriesRef.current = null
    }
  }, [chartLib, chartData, height, showVolume, handleCandleUpdate])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center text-red-500" style={{ height }}>
        <p>{error}</p>
      </div>
    )
  }

  if (!chartData) {
    return (
      <div className="flex items-center justify-center text-gray-500" style={{ height }}>
        <p>No chart data available</p>
      </div>
    )
  }

  const hasOscillators = chartData.indicators.some((ind) => ind.pane === 'oscillator')

  return (
    <div className="space-y-4">
      {/* Chart Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">
            {chartData.symbol} - {chartData.strategy_name}
          </h3>
          <p className="text-xs text-gray-500">
            Interval: {chartData.interval} | Candles: {chartData.candles.length}
          </p>
        </div>
        {enableRealtime && (
          <div className="flex items-center gap-2 text-xs">
            <Circle
              className={cn(
                'h-2 w-2 fill-current',
                wsState.isConnected ? 'text-green-500 animate-pulse' : 'text-gray-400'
              )}
            />
            <span className="text-gray-500">{wsState.isConnected ? 'Live' : 'Historical'}</span>
          </div>
        )}
      </div>

      {/* Chart Legend */}
      <div className="space-y-2">
        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span>Buy Entry</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            <span>Sell Entry</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-orange-500"></span>
            <span>Exit</span>
          </div>
        </div>
        {chartData.indicators && chartData.indicators.length > 0 && (
          <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span className="font-medium">Indicators:</span>
            {chartData.indicators.map((indicator, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <span className="w-3 h-0.5" style={{ backgroundColor: indicator.color }}></span>
                <span>{indicator.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Chart Container */}
      <div ref={chartContainerRef} className="w-full bg-gray-50 dark:bg-gray-900 rounded-lg" />

      {/* Oscillator Chart Container (RSI, etc.) */}
      {hasOscillators && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {chartData.indicators.find((ind) => ind.pane === 'oscillator')?.name || 'Oscillator'}
          </h4>
          <div
            ref={oscillatorChartRef}
            className="w-full bg-gray-50 dark:bg-gray-900 rounded-lg"
          />
        </div>
      )}
    </div>
  )
}
