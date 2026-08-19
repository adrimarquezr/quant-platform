import { useNavigate } from 'react-router-dom';
import { Briefcase } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { usePortfolios } from '@/hooks/use-portfolios';
import { formatCurrency, formatDate } from '@/lib/utils';
import type { PortfolioSummary } from '@/api/types';

export function PortfolioList() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = usePortfolios();

  return (
    <div className="space-y-4 animate-fade-in">
      <Card accent padding="none">
        <div className="px-4 pt-4">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Briefcase className="w-4 h-4" />
                Portfolios
              </span>
            </CardTitle>
          </CardHeader>
        </div>

        {isLoading ? (
          <div className="p-4"><LoadingState /></div>
        ) : isError ? (
          <div className="p-4"><ErrorState message={error.message} onRetry={() => void refetch()} /></div>
        ) : !data?.length ? (
          <div className="p-4">
            <EmptyState
              title="No portfolios"
              description="Create a portfolio to start tracking positions and performance."
            />
          </div>
        ) : (
          <DataTable<PortfolioSummary>
            columns={[
              {
                key: 'name', header: 'Name',
                render: (p) => <span className="font-medium text-[var(--color-text-primary)]">{p.name}</span>,
              },
              {
                key: 'value', header: 'Total Value',
                render: (p) => <span className="font-mono">{formatCurrency(p.total_value)}</span>,
              },
              {
                key: 'cash', header: 'Cash',
                render: (p) => <span className="font-mono text-[var(--color-text-muted)]">{formatCurrency(p.cash)}</span>,
              },
              {
                key: 'updated', header: 'Updated',
                render: (p) => <span className="text-xs text-[var(--color-text-muted)]">{formatDate(p.updated_at)}</span>,
              },
            ]}
            data={data}
            keyExtractor={(p) => p.id}
            onRowClick={(p) => navigate(`/portfolios/${p.id}`)}
          />
        )}
      </Card>
    </div>
  );
}
