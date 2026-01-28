'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2, TrendingUp, BarChart3 } from 'lucide-react'
import { backtestApi } from '@/lib/api'
import { BacktestChartData, CandleData, ChartMarker, EquityCurvePoint, IndicatorSeries } from '@/types/backtest'
import { cn } from '@/lib/utils'

interface BacktestChartProps {
  backtestId: string
  symbol: string
}

type ChartView = 'price' | 'equity'

export function BacktestChart({ backtestId, symbol }: BacktestChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const rsiChartContainerRef = useRef<HTMLDivElement>(null)
  const macdChartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const rsiChartRef = useRef<any>(null)
  const macdChartRef = useRef<any>(null)
  const [chartData, setChartData] = useState<BacktestChartData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [chartView, setChartView] = useState<ChartView>('price')
  const [chartLib, setChartLib] = useState<any>(null)

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
    const fetchData = async () => {
      setIsLoading(true)
      try {
        const data = await backtestApi.getChartData(backtestId)
        setChartData(data)
      } catch (err) {
        console.error('Failed to fetch chart data:', err)
        setError('Failed to load chart data')
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [backtestId])

  // Create/update chart
  useEffect(() => {
    if (!chartLib || !chartData || !chartContainerRef.current) return

    // Clean up existing chart
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    const { createChart, ColorType, CrosshairMode } = chartLib

    // In v5, series types might be accessed differently
    const CandlestickSeries = chartLib.CandlestickSeries
    const HistogramSeries = chartLib.HistogramSeries
    const AreaSeries = chartLib.AreaSeries
    const LineSeries = chartLib.LineSeries

    // IST timezone offset in seconds (UTC+5:30 = 5.5 hours = 19800 seconds)
    const IST_OFFSET_SECONDS = 5.5 * 60 * 60

    // Format time in IST
    const formatTimeIST = (timestamp: number) => {
      const date = new Date((timestamp + IST_OFFSET_SECONDS) * 1000)
      const hours = date.getUTCHours().toString().padStart(2, '0')
      const minutes = date.getUTCMinutes().toString().padStart(2, '0')
      return `${hours}:${minutes}`
    }

    // Format date in IST
    const formatDateIST = (timestamp: number) => {
      const date = new Date((timestamp + IST_OFFSET_SECONDS) * 1000)
      const day = date.getUTCDate().toString().padStart(2, '0')
      const month = (date.getUTCMonth() + 1).toString().padStart(2, '0')
      const year = date.getUTCFullYear()
      return `${day}/${month}/${year}`
    }

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
      localization: {
        timeFormatter: (timestamp: number) => formatTimeIST(timestamp),
        dateFormatter: (timestamp: number) => formatDateIST(timestamp),
      },
      handleScroll: {
        vertTouchDrag: false,
      },
    })

    if (chartView === 'price') {
      // Candlestick chart - try v5 API first, fallback to v4
      const candleOptions = {
        upColor: '#10B981',
        downColor: '#EF4444',
        borderDownColor: '#EF4444',
        borderUpColor: '#10B981',
        wickDownColor: '#EF4444',
        wickUpColor: '#10B981',
      }

      let candlestickSeries: any
      if (CandlestickSeries && typeof chart.addSeries === 'function') {
        // v5 API
        candlestickSeries = chart.addSeries(CandlestickSeries, candleOptions)
      } else if (typeof chart.addCandlestickSeries === 'function') {
        // v4 API fallback
        candlestickSeries = chart.addCandlestickSeries(candleOptions)
      } else {
        console.error('Unable to create candlestick series')
        return
      }

      // Convert candle data
      const candleData = chartData.candles.map((candle: CandleData) => ({
        time: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }))
      candlestickSeries.setData(candleData)

      // Add markers for trades (v5 API - check if method exists)
      if (chartData.markers && chartData.markers.length > 0) {
        const markers = chartData.markers.map((marker: ChartMarker) => ({
          time: marker.time,
          position: marker.position,
          color: marker.color,
          shape: marker.shape,
          text: marker.text,
        }))
        // setMarkers may be on the series or accessed differently in v5
        if (typeof candlestickSeries.setMarkers === 'function') {
          candlestickSeries.setMarkers(markers)
        } else if (typeof chart.setMarkers === 'function') {
          chart.setMarkers(candlestickSeries, markers)
        }
      }

      // Add indicator overlays on main price pane
      if (chartData.indicators) {
        chartData.indicators.forEach((indicator: IndicatorSeries) => {
          if (indicator.pane === 'main' && indicator.type === 'line') {
            // Add as line series overlay on price chart
            const lineOptions = {
              color: indicator.color || '#6366F1',
              lineWidth: 2,
              priceLineVisible: false,
              lastValueVisible: true,
              title: indicator.name,
            }

            let lineSeries: any
            if (LineSeries && typeof chart.addSeries === 'function') {
              lineSeries = chart.addSeries(LineSeries, lineOptions)
            } else if (typeof chart.addLineSeries === 'function') {
              lineSeries = chart.addLineSeries(lineOptions)
            }

            if (lineSeries) {
              const lineData = indicator.data
                .filter(d => d.value !== null)
                .map(d => ({
                  time: d.time,
                  value: d.value,
                }))
              lineSeries.setData(lineData)
            }
          }
        })
      }

      // Add volume if available
      if (chartData.candles.some((c: CandleData) => c.volume)) {
        const volumeOptions = {
          color: '#6366F1',
          priceFormat: { type: 'volume' },
          priceScaleId: '',
        }

        let volumeSeries: any
        if (HistogramSeries && typeof chart.addSeries === 'function') {
          volumeSeries = chart.addSeries(HistogramSeries, volumeOptions)
        } else if (typeof chart.addHistogramSeries === 'function') {
          volumeSeries = chart.addHistogramSeries(volumeOptions)
        }

        if (volumeSeries) {
          volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
          })
          const volumeData = chartData.candles
            .filter((c: CandleData) => c.volume !== undefined)
            .map((candle: CandleData) => ({
              time: candle.time,
              value: candle.volume,
              color: candle.close >= candle.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
            }))
          volumeSeries.setData(volumeData)
        }
      }
    } else {
      // Equity curve chart - try v5 API first, fallback to v4
      const areaOptions = {
        lineColor: '#6366F1',
        topColor: 'rgba(99, 102, 241, 0.4)',
        bottomColor: 'rgba(99, 102, 241, 0.0)',
        lineWidth: 2,
      }

      let equitySeries: any
      if (AreaSeries && typeof chart.addSeries === 'function') {
        equitySeries = chart.addSeries(AreaSeries, areaOptions)
      } else if (typeof chart.addAreaSeries === 'function') {
        equitySeries = chart.addAreaSeries(areaOptions)
      } else if (LineSeries && typeof chart.addSeries === 'function') {
        // Fallback to line series
        equitySeries = chart.addSeries(LineSeries, { color: '#6366F1', lineWidth: 2 })
      } else if (typeof chart.addLineSeries === 'function') {
        equitySeries = chart.addLineSeries({ color: '#6366F1', lineWidth: 2 })
      }

      if (equitySeries) {
        const equityData = chartData.equity_curve.map((point: EquityCurvePoint) => ({
          time: point.time,
          value: point.value,
        }))
        equitySeries.setData(equityData)
      }
    }

    chart.timeScale().fitContent()
    chartRef.current = chart

    // Create RSI chart if RSI indicators exist
    if (chartView === 'price' && chartData.indicators) {
      const rsiIndicators = chartData.indicators.filter(ind => ind.pane === 'rsi')
      if (rsiIndicators.length > 0 && rsiChartContainerRef.current) {
        // Clean up existing RSI chart
        if (rsiChartRef.current) {
          rsiChartRef.current.remove()
          rsiChartRef.current = null
        }

        const rsiChart = createChart(rsiChartContainerRef.current, {
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
          localization: {
            timeFormatter: (timestamp: number) => formatTimeIST(timestamp),
            dateFormatter: (timestamp: number) => formatDateIST(timestamp),
          },
          height: 150,
        })

        rsiIndicators.forEach((indicator: IndicatorSeries) => {
          const lineOptions = {
            color: indicator.color || '#8B5CF6',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: true,
          }

          let lineSeries: any
          if (LineSeries && typeof rsiChart.addSeries === 'function') {
            lineSeries = rsiChart.addSeries(LineSeries, lineOptions)
          } else if (typeof rsiChart.addLineSeries === 'function') {
            lineSeries = rsiChart.addLineSeries(lineOptions)
          }

          if (lineSeries) {
            const lineData = indicator.data
              .filter(d => d.value !== null)
              .map(d => ({
                time: d.time,
                value: d.value,
              }))
            lineSeries.setData(lineData)
          }
        })

        // Add reference lines for RSI at 30 and 70
        rsiChart.priceScale('right').applyOptions({
          scaleMargins: { top: 0.1, bottom: 0.1 },
        })

        rsiChart.timeScale().fitContent()
        rsiChartRef.current = rsiChart
      }

      // Create MACD chart if MACD indicators exist
      const macdIndicators = chartData.indicators.filter(ind => ind.pane === 'macd')
      if (macdIndicators.length > 0 && macdChartContainerRef.current) {
        // Clean up existing MACD chart
        if (macdChartRef.current) {
          macdChartRef.current.remove()
          macdChartRef.current = null
        }

        const macdChart = createChart(macdChartContainerRef.current, {
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
          localization: {
            timeFormatter: (timestamp: number) => formatTimeIST(timestamp),
            dateFormatter: (timestamp: number) => formatDateIST(timestamp),
          },
          height: 150,
        })

        macdIndicators.forEach((indicator: IndicatorSeries) => {
          // MACD Line
          const lineOptions = {
            color: indicator.color || '#3B82F6',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: true,
          }

          let lineSeries: any
          if (LineSeries && typeof macdChart.addSeries === 'function') {
            lineSeries = macdChart.addSeries(LineSeries, lineOptions)
          } else if (typeof macdChart.addLineSeries === 'function') {
            lineSeries = macdChart.addLineSeries(lineOptions)
          }

          if (lineSeries) {
            const lineData = indicator.data
              .filter(d => d.value !== null)
              .map(d => ({
                time: d.time,
                value: d.value,
              }))
            lineSeries.setData(lineData)
          }

          // Signal Line
          if (indicator.signal_line) {
            const signalOptions = {
              color: '#F59E0B',
              lineWidth: 2,
              priceLineVisible: false,
              lastValueVisible: true,
            }

            let signalSeries: any
            if (LineSeries && typeof macdChart.addSeries === 'function') {
              signalSeries = macdChart.addSeries(LineSeries, signalOptions)
            } else if (typeof macdChart.addLineSeries === 'function') {
              signalSeries = macdChart.addLineSeries(signalOptions)
            }

            if (signalSeries) {
              const signalData = indicator.signal_line
                .filter(d => d.value !== null)
                .map(d => ({
                  time: d.time,
                  value: d.value,
                }))
              signalSeries.setData(signalData)
            }
          }

          // Histogram
          if (indicator.histogram) {
            const histogramOptions = {
              color: '#6366F1',
              priceFormat: { type: 'volume' },
            }

            let histogramSeries: any
            if (HistogramSeries && typeof macdChart.addSeries === 'function') {
              histogramSeries = macdChart.addSeries(HistogramSeries, histogramOptions)
            } else if (typeof macdChart.addHistogramSeries === 'function') {
              histogramSeries = macdChart.addHistogramSeries(histogramOptions)
            }

            if (histogramSeries) {
              const histData = indicator.histogram
                .filter(d => d.value !== null)
                .map(d => ({
                  time: d.time,
                  value: d.value,
                  color: (d.value ?? 0) >= 0 ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)',
                }))
              histogramSeries.setData(histData)
            }
          }
        })

        macdChart.timeScale().fitContent()
        macdChartRef.current = macdChart
      }
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
      if (rsiChartContainerRef.current && rsiChartRef.current) {
        rsiChartRef.current.applyOptions({
          width: rsiChartContainerRef.current.clientWidth,
        })
      }
      if (macdChartContainerRef.current && macdChartRef.current) {
        macdChartRef.current.applyOptions({
          width: macdChartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
      if (rsiChartRef.current) {
        rsiChartRef.current.remove()
        rsiChartRef.current = null
      }
      if (macdChartRef.current) {
        macdChartRef.current.remove()
        macdChartRef.current = null
      }
    }
  }, [chartLib, chartData, chartView])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96 text-red-500">
        <p>{error}</p>
      </div>
    )
  }

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-500">
        <p>No chart data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Chart Type Toggle */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{symbol} - {chartView === 'price' ? 'Price Chart' : 'Equity Curve'}</h3>
        <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setChartView('price')}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors',
              chartView === 'price'
                ? 'bg-white dark:bg-gray-700 shadow-sm'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            )}
          >
            <TrendingUp className="h-4 w-4" />
            Price
          </button>
          <button
            onClick={() => setChartView('equity')}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-colors',
              chartView === 'equity'
                ? 'bg-white dark:bg-gray-700 shadow-sm'
                : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
            )}
          >
            <BarChart3 className="h-4 w-4" />
            Equity
          </button>
        </div>
      </div>

      {/* Chart Legend */}
      {chartView === 'price' && (
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
              <span className="w-3 h-3 rounded-full border-2 border-gray-400 bg-transparent"></span>
              <span>Exit</span>
            </div>
          </div>
          {chartData.indicators && chartData.indicators.length > 0 && (
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium">Indicators:</span>
              {chartData.indicators.map((indicator, idx) => (
                <div key={idx} className="flex items-center gap-1">
                  <span
                    className="w-3 h-0.5"
                    style={{ backgroundColor: indicator.color || '#6366F1' }}
                  ></span>
                  <span>{indicator.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main Chart Container */}
      <div
        ref={chartContainerRef}
        className="h-96 w-full bg-gray-50 dark:bg-gray-900 rounded-lg"
      />

      {/* RSI Chart Container */}
      {chartView === 'price' && chartData?.indicators?.some(ind => ind.pane === 'rsi') && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">RSI Indicator</h4>
          <div
            ref={rsiChartContainerRef}
            className="h-36 w-full bg-gray-50 dark:bg-gray-900 rounded-lg"
          />
        </div>
      )}

      {/* MACD Chart Container */}
      {chartView === 'price' && chartData?.indicators?.some(ind => ind.pane === 'macd') && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">MACD Indicator</h4>
          <div
            ref={macdChartContainerRef}
            className="h-36 w-full bg-gray-50 dark:bg-gray-900 rounded-lg"
          />
        </div>
      )}
    </div>
  )
}
