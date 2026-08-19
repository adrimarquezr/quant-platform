import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
      <Loader2 className="w-8 h-8 text-[var(--color-info)] animate-spin mb-3" />
      <p className="text-sm text-[var(--color-text-muted)]">{message}</p>
    </div>
  );
}

export function EmptyState({
  title = 'No data',
  description = 'There are no items to display.',
  action,
}: {
  title?: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
      <Inbox className="w-12 h-12 text-[var(--color-text-muted)] mb-4 opacity-50" />
      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-1">{title}</h3>
      <p className="text-xs text-[var(--color-text-muted)] max-w-xs text-center">{description}</p>
      {action && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

export function ErrorState({
  title = 'Error',
  message = 'Something went wrong.',
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
      <AlertTriangle className="w-10 h-10 text-[var(--color-negative)] mb-3 opacity-75" />
      <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-1">{title}</h3>
      <p className="text-xs text-[var(--color-text-muted)] max-w-xs text-center mb-3">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </Button>
      )}
    </div>
  );
}
