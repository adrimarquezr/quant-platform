import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatPercent, formatDate } from '@/lib/utils';

interface DrawdownChartProps {
  dates: string[];
  equityCurve: number[];
  height?: number;
}

export function DrawdownChart({ dates, equityCurve, height = 200 }: DrawdownChartProps) {
  // Compute drawdown from equity curve
  let peak = equityCurve[0] ?? 0;
  const data = dates.map((date, i) => {
    const value = equityCurve[i] ?? 0;
    if (value > peak) peak = value;
    const drawdown = peak > 0 ? (value - peak) / peak : 0;
    return { date, drawdown };
  });

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-[var(--color-text-muted)]" style={{ height }}>
        No drawdown data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <defs>
          <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-negative)" stopOpacity={0} />
            <stop offset="95%" stopColor="var(--color-negative)" stopOpacity={0.3} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-primary)" />
        <XAxis
          dataKey="date"
          tickFormatter={(v: string) => formatDate(v)}
          tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
          axisLine={{ stroke: 'var(--color-border-primary)' }}
          tickLine={false}
          minTickGap={60}
        />
        <YAxis
          tickFormatter={(v: number) => formatPercent(v, 1)}
          tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          width={60}
          domain={['dataMin', 0]}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border-secondary)',
            borderRadius: 'var(--radius-md)',
            fontSize: 12,
            color: 'var(--color-text-primary)',
          }}
          labelFormatter={(v: string) => formatDate(v)}
          formatter={(v: number) => [formatPercent(v), 'Drawdown']}
        />
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="var(--color-negative)"
          strokeWidth={1.5}
          fill="url(#drawdownGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
