import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { useStrategySchema } from '@/hooks/use-strategies';

export function StrategyDetail() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useStrategySchema(name ?? '');

  if (isLoading) return <LoadingState message="Loading strategy..." />;
  if (isError) return <ErrorState message={error.message} />;
  if (!data) return <ErrorState message="Strategy not found" />;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Back & Actions */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigate('/strategies')}>
          <ArrowLeft className="w-4 h-4" />
          Back to Strategies
        </Button>
        <Button size="sm" onClick={() => navigate(`/backtesting/new?strategy=${name}`)}>
          <Play className="w-4 h-4" />
          Run Backtest
        </Button>
      </div>

      {/* Strategy Info */}
      <Card accent>
        <CardHeader>
          <CardTitle>{data.strategy_name}</CardTitle>
          <Badge variant="info">v{data.version}</Badge>
        </CardHeader>
      </Card>

      {/* Parameter Schema */}
      <Card>
        <CardHeader>
          <CardTitle>Parameter Schema</CardTitle>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border-primary)]">
                <th className="px-4 py-2 text-left text-xs font-semibold text-[var(--color-text-muted)] uppercase">Parameter</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-[var(--color-text-muted)] uppercase">Type</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-[var(--color-text-muted)] uppercase">Default</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-[var(--color-text-muted)] uppercase">Min</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-[var(--color-text-muted)] uppercase">Max</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.parameters).map(([key, param]) => (
                <tr key={key} className="border-b border-[var(--color-border-primary)]">
                  <td className="px-4 py-2.5 font-mono text-[var(--color-text-primary)]">{key}</td>
                  <td className="px-4 py-2.5">
                    <Badge>{param.type}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-[var(--color-text-accent)]">{String(param.default)}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-[var(--color-text-muted)]">{param.min ?? '—'}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-[var(--color-text-muted)]">{param.max ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
