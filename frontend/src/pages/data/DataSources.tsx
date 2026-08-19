import { useNavigate } from 'react-router-dom';
import { Database, ExternalLink } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { LoadingState, EmptyState } from '@/components/ui/States';
import { useSymbols } from '@/hooks/use-market-data';

export function DataSources() {
  const navigate = useNavigate();
  const symbols = useSymbols();

  return (
    <div className="space-y-4 animate-fade-in">
      <Card accent>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2">
              <Database className="w-4 h-4" />
              Ingested Symbols
            </span>
          </CardTitle>
        </CardHeader>

        {symbols.isLoading ? (
          <LoadingState />
        ) : !symbols.data?.length ? (
          <EmptyState
            title="No data sources"
            description="Ingest market data via the Data Explorer."
            action={{ label: 'Go to Data Explorer', onClick: () => navigate('/data/explorer') }}
          />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {symbols.data.map((sym) => (
              <div
                key={sym}
                onClick={() => navigate(`/data/explorer?symbol=${sym}`)}
                className="flex items-center justify-between p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-hover)] transition-colors cursor-pointer group"
              >
                <span className="font-mono text-sm font-medium text-[var(--color-text-primary)]">{sym}</span>
                <ExternalLink className="w-3.5 h-3.5 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Data Provider Info */}
      <Card>
        <CardHeader>
          <CardTitle>Data Providers</CardTitle>
        </CardHeader>
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)]">
            <div>
              <p className="text-sm font-medium text-[var(--color-text-primary)]">Yahoo Finance</p>
              <p className="text-xs text-[var(--color-text-muted)]">Daily OHLCV via yfinance</p>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs bg-[var(--color-positive-soft)] text-[var(--color-positive)]">Active</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
