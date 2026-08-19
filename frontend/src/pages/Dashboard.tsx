import { useNavigate } from 'react-router-dom';
import { Activity, Brain, LineChart, Play, Briefcase, Database } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { MetricCard } from '@/components/ui/MetricCard';
import { StatusBadge } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { useHealth } from '@/hooks/use-health';
import { useStrategies } from '@/hooks/use-strategies';
import { useBacktests } from '@/hooks/use-backtests';
import { useSymbols } from '@/hooks/use-market-data';
import { usePortfolios } from '@/hooks/use-portfolios';
import { formatPercent, formatRatio, formatDuration } from '@/lib/utils';
import type { BacktestSummary } from '@/api/types';

export function Dashboard() {
  const navigate = useNavigate();
  const health = useHealth();
  const strategies = useStrategies();
  const backtests = useBacktests();
  const symbols = useSymbols();
  const portfolios = usePortfolios();

  const isLoading = health.isLoading && strategies.isLoading;

  if (isLoading) return <LoadingState message="Loading dashboard..." />;

  // Compute summary metrics from available data
  const latestBacktest = backtests.data?.[0];
  const totalBacktests = backtests.data?.length ?? 0;
  const totalStrategies = strategies.data?.length ?? 0;
  const totalSymbols = symbols.data?.length ?? 0;
  const totalPortfolios = portfolios.data?.length ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="System Status"
          value={health.data?.status === 'healthy' ? 'Online' : 'Offline'}
          format="raw"
        />
        <MetricCard
          label="Strategies"
          value={totalStrategies}
          format="number"
        />
        <MetricCard
          label="Backtests"
          value={totalBacktests}
          format="number"
        />
        <MetricCard
          label="Symbols"
          value={totalSymbols}
          format="number"
        />
        <MetricCard
          label="Portfolios"
          value={totalPortfolios}
          format="number"
        />
        <MetricCard
          label="Best Sharpe"
          value={latestBacktest?.sharpe_ratio}
          format="ratio"
        />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Backtests */}
        <Card accent>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Play className="w-4 h-4" />
                Recent Backtests
              </span>
            </CardTitle>
          </CardHeader>
          {backtests.isLoading ? (
            <LoadingState />
          ) : backtests.isError ? (
            <ErrorState message="Failed to load backtests" onRetry={() => void backtests.refetch()} />
          ) : !backtests.data?.length ? (
            <EmptyState
              title="No backtests yet"
              description="Run your first backtest to see results here."
              action={{ label: 'New Backtest', onClick: () => navigate('/backtesting/new') }}
            />
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
                  key: 'return', header: 'Return',
                  render: (bt) => (
                    <span className={bt.total_return != null && bt.total_return > 0 ? 'metric-positive' : 'metric-negative'}>
                      {formatPercent(bt.total_return)}
                    </span>
                  ),
                },
                {
                  key: 'sharpe', header: 'Sharpe',
                  render: (bt) => <span className="font-mono text-xs">{formatRatio(bt.sharpe_ratio)}</span>,
                },
                {
                  key: 'time', header: 'Time',
                  render: (bt) => <span className="text-[var(--color-text-muted)]">{formatDuration(bt.execution_time_ms)}</span>,
                },
              ]}
              data={backtests.data.slice(0, 5)}
              keyExtractor={(bt) => bt.id}
              onRowClick={(bt) => navigate(`/backtesting/results/${bt.id}`)}
            />
          )}
        </Card>

        {/* Quick Actions */}
        <div className="space-y-4">
          <Card accent>
            <CardHeader>
              <CardTitle>
                <span className="flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Quick Actions
                </span>
              </CardTitle>
            </CardHeader>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'New Backtest', icon: Play, path: '/backtesting/new', color: 'var(--color-chart-1)' },
                { label: 'Data Explorer', icon: LineChart, path: '/data/explorer', color: 'var(--color-chart-3)' },
                { label: 'Strategies', icon: Brain, path: '/strategies', color: 'var(--color-chart-2)' },
                { label: 'Portfolios', icon: Briefcase, path: '/portfolios', color: 'var(--color-chart-4)' },
              ].map((action) => (
                <button
                  key={action.path}
                  onClick={() => navigate(action.path)}
                  className="flex items-center gap-3 p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] transition-colors cursor-pointer text-left"
                >
                  <action.icon className="w-5 h-5 flex-shrink-0" style={{ color: action.color }} />
                  <span className="text-sm text-[var(--color-text-secondary)]">{action.label}</span>
                </button>
              ))}
            </div>
          </Card>

          {/* Available Strategies */}
          <Card accent>
            <CardHeader>
              <CardTitle>
                <span className="flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  Active Strategies
                </span>
              </CardTitle>
            </CardHeader>
            {strategies.isLoading ? (
              <LoadingState />
            ) : !strategies.data?.length ? (
              <EmptyState title="No strategies" description="No strategies registered." />
            ) : (
              <div className="space-y-2">
                {strategies.data.map((s) => (
                  <div
                    key={s.name}
                    onClick={() => navigate(`/strategies/${s.name}`)}
                    className="flex items-center justify-between p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] transition-colors cursor-pointer"
                  >
                    <div>
                      <p className="text-sm font-medium text-[var(--color-text-primary)]">{s.name}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">v{s.version} · {s.category}</p>
                    </div>
                    <span className="text-xs text-[var(--color-text-muted)] font-mono">
                      {Object.keys(s.parameter_schema).length} params
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Data Status */}
          <Card accent>
            <CardHeader>
              <CardTitle>
                <span className="flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Ingested Data
                </span>
              </CardTitle>
            </CardHeader>
            {symbols.isLoading ? (
              <LoadingState />
            ) : !symbols.data?.length ? (
              <EmptyState
                title="No data ingested"
                description="Ingest market data to get started."
                action={{ label: 'Data Explorer', onClick: () => navigate('/data/explorer') }}
              />
            ) : (
              <div className="flex flex-wrap gap-2">
                {symbols.data.map((sym) => (
                  <span
                    key={sym}
                    onClick={() => navigate(`/data/explorer?symbol=${sym}`)}
                    className="px-2.5 py-1 rounded-[var(--radius-sm)] bg-[var(--color-bg-tertiary)] text-xs font-mono text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] cursor-pointer transition-colors"
                  >
                    {sym}
                  </span>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
