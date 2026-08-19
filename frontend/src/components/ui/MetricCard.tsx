import { cn, metricColor, formatPercent, formatCurrency, formatRatio } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  format?: 'percent' | 'currency' | 'ratio' | 'number' | 'raw';
  trend?: 'up' | 'down' | 'neutral';
  subtitle?: string;
  className?: string;
}

export function MetricCard({
  label,
  value,
  format = 'raw',
  trend,
  subtitle,
  className,
}: MetricCardProps) {
  const numericValue = typeof value === 'number' ? value : null;

  const formattedValue = (() => {
    if (value == null) return '—';
    if (typeof value === 'string') return value;
    switch (format) {
      case 'percent': return formatPercent(value);
      case 'currency': return formatCurrency(value);
      case 'ratio': return formatRatio(value);
      case 'number': return value.toLocaleString();
      default: return String(value);
    }
  })();

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const autoTrend = trend ?? (numericValue != null && numericValue > 0 ? 'up' : numericValue != null && numericValue < 0 ? 'down' : 'neutral');

  return (
    <div className={cn('glass-card p-4', className)}>
      <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">
        {label}
      </p>
      <div className="flex items-end gap-2">
        <p className={cn(
          'text-xl font-semibold font-[var(--font-mono)]',
          format === 'percent' || format === 'ratio' ? metricColor(numericValue) : 'text-[var(--color-text-primary)]',
        )}>
          {formattedValue}
        </p>
        {numericValue != null && (
          <TrendIcon className={cn(
            'w-4 h-4 mb-0.5',
            autoTrend === 'up' ? 'text-[var(--color-positive)]' :
            autoTrend === 'down' ? 'text-[var(--color-negative)]' :
            'text-[var(--color-text-muted)]',
          )} />
        )}
      </div>
      {subtitle && (
        <p className="text-xs text-[var(--color-text-muted)] mt-1">{subtitle}</p>
      )}
    </div>
  );
}
