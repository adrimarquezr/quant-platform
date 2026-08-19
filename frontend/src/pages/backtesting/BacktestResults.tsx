import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, BarChart3 } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { MetricCard } from '@/components/ui/MetricCard';
import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/Badge';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { EquityCurve } from '@/components/charts/EquityCurve';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { useBacktest } from '@/hooks/use-backtests';
import { formatDuration } from '@/lib/utils';

export function BacktestResults() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useBacktest(id ?? '');

  if (isLoading) return <LoadingState message="Loading results..." />;
  if (isError) return <ErrorState message={error.message} />;
  if (!data) return <ErrorState message="Backtest not found" />;

  const { metrics } = data;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigate('/backtesting/runs')}>
          <ArrowLeft className="w-4 h-4" />
          Back to Runs
        </Button>
        <div className="flex items-center gap-3">
          <StatusBadge status={data.status} />
          <span className="text-xs text-[var(--color-text-muted)]">{formatDuration(data.execution_time_ms)}</span>
        </div>
      </div>

      {/* Strategy Info */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{data.strategy_name}</h2>
            <p className="text-xs text-[var(--color-text-muted)] font-mono mt-0.5">ID: {data.id}</p>
          </div>
          <BarChart3 className="w-5 h-5 text-[var(--color-text-muted)]" />
        </div>
      </Card>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard label="Total Return" value={metrics.total_return} format="percent" />
        <MetricCard label="CAGR" value={metrics.cagr} format="percent" />
        <MetricCard label="Sharpe Ratio" value={metrics.sharpe_ratio} format="ratio" />
        <MetricCard label="Sortino Ratio" value={metrics.sortino_ratio} format="ratio" />
        <MetricCard label="Calmar Ratio" value={metrics.calmar_ratio} format="ratio" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard label="Max Drawdown" value={metrics.max_drawdown} format="percent" trend="down" />
        <MetricCard label="Volatility" value={metrics.annualized_volatility} format="percent" />
        <MetricCard label="Win Rate" value={metrics.win_rate} format="percent" />
        <MetricCard label="Profit Factor" value={metrics.profit_factor} format="ratio" />
        <MetricCard label="Total Trades" value={metrics.total_trades} format="number" />
      </div>

      {/* Equity Curve */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
          <span className="text-xs text-[var(--color-text-muted)] font-mono">
            Final: ${metrics.final_equity.toLocaleString()}
          </span>
        </CardHeader>
        <EquityCurve dates={data.dates} values={data.equity_curve} height={350} />
      </Card>

      {/* Drawdown */}
      <Card>
        <CardHeader>
          <CardTitle>Drawdown</CardTitle>
        </CardHeader>
        <DrawdownChart dates={data.dates} equityCurve={data.equity_curve} height={200} />
      </Card>

      {/* Additional Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Trade Statistics</CardTitle>
        </CardHeader>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-[var(--color-text-muted)] mb-0.5">Avg Trade Return</p>
            <p className={`font-mono text-sm ${metrics.avg_trade_return > 0 ? 'metric-positive' : 'metric-negative'}`}>
              {(metrics.avg_trade_return * 100).toFixed(3)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)] mb-0.5">Best Trade</p>
            <p className="font-mono text-sm metric-positive">{(metrics.best_trade * 100).toFixed(3)}%</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)] mb-0.5">Worst Trade</p>
            <p className="font-mono text-sm metric-negative">{(metrics.worst_trade * 100).toFixed(3)}%</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)] mb-0.5">Exposure Time</p>
            <p className="font-mono text-sm">{(metrics.exposure_time * 100).toFixed(1)}%</p>
          </div>
        </div>
      </Card>

      {/* Config */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <pre className="text-xs text-[var(--color-text-secondary)] font-mono bg-[var(--color-bg-tertiary)] rounded-[var(--radius-md)] p-3 overflow-x-auto">
          {JSON.stringify(data.config, null, 2)}
        </pre>
      </Card>
    </div>
  );
}
