import { useEffect, useRef } from 'react';
import { createChart, type IChartApi, type CandlestickData, ColorType } from 'lightweight-charts';
import type { PriceBar } from '@/api/types';

interface CandlestickChartProps {
  data: PriceBar[];
  height?: number;
}

export function CandlestickChart({ data, height = 400 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
        fontFamily: "'Inter', system-ui, sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        vertLine: { color: '#334155', width: 1, style: 3 },
        horzLine: { color: '#334155', width: 1, style: 3 },
      },
      rightPriceScale: {
        borderColor: '#1e293b',
      },
      timeScale: {
        borderColor: '#1e293b',
        timeVisible: false,
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    const chartData: CandlestickData[] = data.map((bar) => ({
      time: bar.timestamp.split('T')[0] as string as unknown as CandlestickData['time'],
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    candlestickSeries.setData(chartData);

    // Volume
    const volumeSeries = chart.addHistogramSeries({
      color: '#3b82f680',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });

    volumeSeries.setData(
      data.map((bar) => ({
        time: bar.timestamp.split('T')[0] as string as unknown as CandlestickData['time'],
        value: bar.volume,
        color: bar.close >= bar.open ? '#22c55e40' : '#ef444440',
      })),
    );

    chart.timeScale().fitContent();
    chartRef.current = chart;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [data, height]);

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-sm text-[var(--color-text-muted)]"
        style={{ height }}
      >
        No price data available
      </div>
    );
  }

  return <div ref={containerRef} className="w-full" />;
}
