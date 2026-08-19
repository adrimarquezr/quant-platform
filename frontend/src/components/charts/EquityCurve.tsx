import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatCurrency, formatDate } from '@/lib/utils';

interface EquityCurveProps {
  dates: string[];
  values: number[];
  height?: number;
}

export function EquityCurve({ dates, values, height = 300 }: EquityCurveProps) {
  const data = dates.map((date, i) => ({
    date,
    value: values[i] ?? 0,
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-[var(--color-text-muted)]" style={{ height }}>
        No equity data
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="var(--color-chart-1)" stopOpacity={0} />
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
          tickFormatter={(v: number) => formatCurrency(v)}
          tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          width={80}
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
          formatter={(v: number) => [formatCurrency(v), 'Equity']}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          fill="url(#equityGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
