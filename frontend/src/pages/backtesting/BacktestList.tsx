import { useNavigate } from 'react-router-dom';
import { List } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { useBacktests } from '@/hooks/use-backtests';
import { formatPercent, formatRatio, formatDuration } from '@/lib/utils';
import type { BacktestSummary } from '@/api/types';

export function BacktestList() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useBacktests();

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div />
        <Button size="sm" onClick={() => navigate('/backtesting/new')}>New Backtest</Button>
      </div>

      <Card accent padding="none">
        <div className="px-4 pt-4">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <List className="w-4 h-4" />
                Backtest Runs
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
              title="No backtests"
              description="Run your first backtest to see results."
              action={{ label: 'New Backtest', onClick: () => navigate('/backtesting/new') }}
            />
          </div>
        ) : (
          <DataTable<BacktestSummary>
            columns={[
              {
                key: 'strategy', header: 'Strategy',
                render: (bt) => <span className="font-medium text-[var(--color-text-primary)]">{bt.strategy_name}</span>,
              },
              {
                key: 'status', header: 'Status',
                render: (bt) => <StatusBadge status={bt.status} />,
              },
              {
                key: 'return', header: 'Total Return',
                render: (bt) => (
                  <span className={`font-mono ${bt.total_return != null && bt.total_return > 0 ? 'metric-positive' : 'metric-negative'}`}>
                    {formatPercent(bt.total_return)}
                  </span>
                ),
              },
              {
                key: 'sharpe', header: 'Sharpe',
                render: (bt) => <span className="font-mono text-xs">{formatRatio(bt.sharpe_ratio)}</span>,
              },
              {
                key: 'drawdown', header: 'Max DD',
                render: (bt) => (
                  <span className="font-mono text-xs metric-negative">
                    {formatPercent(bt.max_drawdown)}
                  </span>
                ),
              },
              {
                key: 'time', header: 'Exec Time',
                render: (bt) => <span className="text-[var(--color-text-muted)] text-xs">{formatDuration(bt.execution_time_ms)}</span>,
              },
            ]}
            data={data}
            keyExtractor={(bt) => bt.id}
            onRowClick={(bt) => navigate(`/backtesting/results/${bt.id}`)}
          />
        )}
      </Card>
    </div>
  );
}
