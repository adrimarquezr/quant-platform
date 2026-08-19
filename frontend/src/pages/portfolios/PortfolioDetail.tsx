import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Wallet } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { MetricCard } from '@/components/ui/MetricCard';
import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState } from '@/components/ui/States';
import { usePortfolio, usePortfolioPositions } from '@/hooks/use-portfolios';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { PositionResponse } from '@/api/types';

export function PortfolioDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const portfolio = usePortfolio(id ?? '');
  const positions = usePortfolioPositions(id ?? '');

  if (portfolio.isLoading) return <LoadingState message="Loading portfolio..." />;
  if (portfolio.isError) return <ErrorState message={portfolio.error.message} />;
  if (!portfolio.data) return <ErrorState message="Portfolio not found" />;

  const p = portfolio.data;

  return (
    <div className="space-y-4 animate-fade-in">
      <Button variant="ghost" size="sm" onClick={() => navigate('/portfolios')}>
        <ArrowLeft className="w-4 h-4" />
        Back to Portfolios
      </Button>

      {/* Portfolio Info */}
      <Card accent>
        <div className="flex items-center gap-3">
          <Wallet className="w-5 h-5 text-[var(--color-info)]" />
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{p.name}</h2>
            {p.description && <p className="text-xs text-[var(--color-text-muted)]">{p.description}</p>}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total Value" value={p.total_value} format="currency" />
        <MetricCard label="Cash" value={p.cash} format="currency" />
        <MetricCard label="Invested" value={p.total_value - p.cash} format="currency" />
      </div>

      {/* Positions */}
      <Card padding="none">
        <div className="px-4 pt-4">
          <CardHeader>
            <CardTitle>Positions</CardTitle>
          </CardHeader>
        </div>
        {positions.isLoading ? (
          <div className="p-4"><LoadingState /></div>
        ) : !positions.data?.length ? (
          <div className="p-8 text-center text-sm text-[var(--color-text-muted)]">No open positions</div>
        ) : (
          <DataTable<PositionResponse>
            columns={[
              { key: 'symbol', header: 'Symbol', render: (pos) => <span className="font-mono font-medium">{pos.symbol}</span> },
              { key: 'qty', header: 'Quantity', render: (pos) => <span className="font-mono">{pos.quantity.toFixed(2)}</span>, className: 'text-right' },
              { key: 'entry', header: 'Avg Entry', render: (pos) => <span className="font-mono">{formatCurrency(pos.avg_entry_price)}</span>, className: 'text-right' },
              { key: 'current', header: 'Current', render: (pos) => <span className="font-mono">{formatCurrency(pos.current_price)}</span>, className: 'text-right' },
              { key: 'value', header: 'Market Value', render: (pos) => <span className="font-mono">{formatCurrency(pos.market_value)}</span>, className: 'text-right' },
              { key: 'pnl', header: 'P&L', render: (pos) => <span className={`font-mono ${pos.unrealized_pnl >= 0 ? 'metric-positive' : 'metric-negative'}`}>{formatCurrency(pos.unrealized_pnl)}</span>, className: 'text-right' },
              { key: 'weight', header: 'Weight', render: (pos) => <span className="font-mono text-xs">{formatPercent(pos.weight)}</span>, className: 'text-right' },
            ]}
            data={positions.data}
            keyExtractor={(pos) => pos.symbol}
          />
        )}
      </Card>
    </div>
  );
}
