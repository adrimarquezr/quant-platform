import { cn } from '@/lib/utils';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

const variantStyles = {
  default: 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)]',
  success: 'bg-[var(--color-positive-soft)] text-[var(--color-positive)]',
  warning: 'bg-[var(--color-warning-soft)] text-[var(--color-warning)]',
  error: 'bg-[var(--color-negative-soft)] text-[var(--color-negative)]',
  info: 'bg-[var(--color-info-soft)] text-[var(--color-info)]',
};

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const variantMap: Record<string, BadgeProps['variant']> = {
    completed: 'success',
    running: 'info',
    pending: 'warning',
    failed: 'error',
    cancelled: 'default',
    passed: 'success',
    approved: 'success',
    rejected: 'error',
    warning: 'warning',
  };

  return (
    <Badge variant={variantMap[status.toLowerCase()] ?? 'default'}>
      <span className={cn(
        'inline-block w-1.5 h-1.5 rounded-full',
        status.toLowerCase() === 'running' && 'pulse-dot',
        status.toLowerCase() === 'completed' ? 'bg-[var(--color-positive)]' :
        status.toLowerCase() === 'running' ? 'bg-[var(--color-info)]' :
        status.toLowerCase() === 'failed' ? 'bg-[var(--color-negative)]' :
        status.toLowerCase() === 'pending' ? 'bg-[var(--color-warning)]' :
        'bg-[var(--color-text-muted)]'
      )} />
      {status}
    </Badge>
  );
}
