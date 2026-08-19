import { useNavigate } from 'react-router-dom';
import { Brain } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { useStrategies } from '@/hooks/use-strategies';
import type { StrategyInfo } from '@/api/types';

export function StrategyList() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useStrategies();

  return (
    <div className="space-y-4 animate-fade-in">
      <Card accent padding="none">
        <div className="px-4 pt-4">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Brain className="w-4 h-4" />
                Registered Strategies
              </span>
            </CardTitle>
          </CardHeader>
        </div>

        {isLoading ? (
          <div className="p-4"><LoadingState /></div>
        ) : isError ? (
          <div className="p-4"><ErrorState message={error.message} onRetry={() => void refetch()} /></div>
        ) : !data?.length ? (
          <div className="p-4"><EmptyState title="No strategies" description="No strategies are registered in the platform." /></div>
        ) : (
          <DataTable<StrategyInfo>
            columns={[
              {
                key: 'name', header: 'Name',
                render: (s) => (
                  <span className="font-medium text-[var(--color-text-primary)]">{s.name}</span>
                ),
              },
              {
                key: 'version', header: 'Version',
                render: (s) => <span className="font-mono text-xs">v{s.version}</span>,
              },
              {
                key: 'category', header: 'Category',
                render: (s) => <Badge variant="info">{s.category}</Badge>,
              },
              {
                key: 'params', header: 'Parameters',
                render: (s) => (
                  <span className="text-[var(--color-text-muted)]">
                    {Object.keys(s.parameter_schema).length} configurable
                  </span>
                ),
              },
            ]}
            data={data}
            keyExtractor={(s) => s.name}
            onRowClick={(s) => navigate(`/strategies/${s.name}`)}
          />
        )}
      </Card>
    </div>
  );
}
