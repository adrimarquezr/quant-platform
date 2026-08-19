import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { useHealth } from '@/hooks/use-health';
import { Badge } from '@/components/ui/Badge';

export function Settings() {
  const { data: health } = useHealth();

  return (
    <div className="max-w-2xl space-y-4 animate-fade-in">
      <Card accent>
        <CardHeader>
          <CardTitle>System Information</CardTitle>
        </CardHeader>
        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-[var(--color-border-primary)]">
            <span className="text-sm text-[var(--color-text-secondary)]">API Status</span>
            <Badge variant={health?.status === 'healthy' ? 'success' : 'error'}>
              {health?.status ?? 'Unknown'}
            </Badge>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[var(--color-border-primary)]">
            <span className="text-sm text-[var(--color-text-secondary)]">API Version</span>
            <span className="text-sm font-mono text-[var(--color-text-primary)]">{health?.version ?? '—'}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[var(--color-border-primary)]">
            <span className="text-sm text-[var(--color-text-secondary)]">Frontend Version</span>
            <span className="text-sm font-mono text-[var(--color-text-primary)]">1.0.0</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-sm text-[var(--color-text-secondary)]">Platform</span>
            <span className="text-sm text-[var(--color-text-primary)]">Quant Platform</span>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <p className="text-sm text-[var(--color-text-muted)]">
          Additional settings (authentication, integrations, data sources) will be available in future releases.
        </p>
      </Card>
    </div>
  );
}
