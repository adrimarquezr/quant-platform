import { clsx, type ClassValue } from 'clsx';

/** Merge class names, filtering falsy values */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/** Format a number as percentage (e.g., 0.1234 → "12.34%") */
export function formatPercent(value: number | null | undefined, decimals = 2): string {
  if (value == null || isNaN(value)) return '—';
  return `${(value * 100).toFixed(decimals)}%`;
}

/** Format a number as currency (e.g., 100000 → "$100,000.00") */
export function formatCurrency(value: number | null | undefined, currency = 'USD'): string {
  if (value == null || isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/** Format a number with fixed decimals */
export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null || isNaN(value)) return '—';
  return value.toFixed(decimals);
}

/** Format a ratio (e.g., Sharpe) */
export function formatRatio(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  return value.toFixed(2);
}

/** Format milliseconds to human-readable duration */
export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
}

/** Format ISO date string to localized short date */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/** Format ISO datetime to relative time (e.g., "2 hours ago") */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);
    const diffDays = Math.floor(diffMs / 86_400_000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  } catch {
    return dateStr;
  }
}

/** Get CSS class for positive/negative values */
export function metricColor(value: number | null | undefined): string {
  if (value == null || value === 0) return 'metric-neutral';
  return value > 0 ? 'metric-positive' : 'metric-negative';
}

/** Determine backtest status display info */
export function getStatusInfo(status: string): { label: string; color: string; bgColor: string } {
  switch (status.toLowerCase()) {
    case 'completed':
      return { label: 'Completed', color: 'text-green-400', bgColor: 'bg-green-400/10' };
    case 'running':
      return { label: 'Running', color: 'text-blue-400', bgColor: 'bg-blue-400/10' };
    case 'pending':
      return { label: 'Pending', color: 'text-yellow-400', bgColor: 'bg-yellow-400/10' };
    case 'failed':
      return { label: 'Failed', color: 'text-red-400', bgColor: 'bg-red-400/10' };
    case 'cancelled':
      return { label: 'Cancelled', color: 'text-gray-400', bgColor: 'bg-gray-400/10' };
    default:
      return { label: status, color: 'text-gray-400', bgColor: 'bg-gray-400/10' };
  }
}
