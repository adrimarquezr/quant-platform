import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Download, Search } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/States';
import { CandlestickChart } from '@/components/charts/CandlestickChart';
import { DataTable } from '@/components/ui/DataTable';
import { useSymbols, usePrices, useIngestData } from '@/hooks/use-market-data';
import { formatCurrency, formatNumber, formatDate } from '@/lib/utils';
import type { PriceBar } from '@/api/types';

export function DataExplorer() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSymbol = searchParams.get('symbol') ?? '';
  const [selectedSymbol, setSelectedSymbol] = useState(initialSymbol);
  const [symbolInput, setSymbolInput] = useState('');
  const [limit, setLimit] = useState(500);

  const symbols = useSymbols();
  const prices = usePrices(selectedSymbol, { limit });
  const ingestMutation = useIngestData();

  const handleSymbolSelect = (sym: string) => {
    setSelectedSymbol(sym);
    setSearchParams({ symbol: sym });
  };

  const handleIngest = () => {
    if (!symbolInput.trim()) return;
    const symbol = symbolInput.trim().toUpperCase();
    ingestMutation.mutate(
      {
        symbol,
        start_date: '2020-01-01',
        end_date: new Date().toISOString().split('T')[0]!,
        frequency: '1d',
        provider: 'yahoo_finance',
      },
      {
        onSuccess: () => {
          setSymbolInput('');
          handleSymbolSelect(symbol);
        },
      },
    );
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Controls Bar */}
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          {/* Symbol Selector */}
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-[var(--color-text-muted)]" />
            <select
              value={selectedSymbol}
              onChange={(e) => handleSymbolSelect(e.target.value)}
              className="flex-1 bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-border-accent)]"
            >
              <option value="">Select symbol...</option>
              {symbols.data?.map((sym) => (
                <option key={sym} value={sym}>{sym}</option>
              ))}
            </select>
          </div>

          {/* Limit */}
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none"
          >
            <option value={100}>100 bars</option>
            <option value={250}>250 bars</option>
            <option value={500}>500 bars</option>
            <option value={1000}>1000 bars</option>
          </select>

          {/* Ingest New */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleIngest()}
              placeholder="New symbol..."
              className="w-28 bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-border-accent)] placeholder:text-[var(--color-text-muted)]"
            />
            <Button
              variant="secondary"
              size="md"
              onClick={handleIngest}
              loading={ingestMutation.isPending}
              disabled={!symbolInput.trim()}
            >
              <Download className="w-3.5 h-3.5" />
              Ingest
            </Button>
          </div>
        </div>
        {ingestMutation.isError && (
          <p className="mt-2 text-xs text-[var(--color-negative)]">
            Failed to ingest: {ingestMutation.error.message}
          </p>
        )}
        {ingestMutation.isSuccess && (
          <p className="mt-2 text-xs text-[var(--color-positive)]">
            Ingested {ingestMutation.data.row_count} rows for {ingestMutation.data.symbol}
          </p>
        )}
      </Card>

      {/* Chart */}
      {selectedSymbol && (
        <Card padding="sm">
          <CardHeader>
            <CardTitle>{selectedSymbol} — OHLCV</CardTitle>
          </CardHeader>
          {prices.isLoading ? (
            <LoadingState message={`Loading ${selectedSymbol} data...`} />
          ) : prices.isError ? (
            <ErrorState message={prices.error.message} onRetry={() => void prices.refetch()} />
          ) : !prices.data?.length ? (
            <EmptyState title="No price data" description={`No OHLCV data for ${selectedSymbol}.`} />
          ) : (
            <CandlestickChart data={prices.data} height={400} />
          )}
        </Card>
      )}

      {/* Data Table */}
      {selectedSymbol && prices.data && prices.data.length > 0 && (
        <Card padding="none">
          <div className="px-4 pt-4">
            <CardHeader>
              <CardTitle>Price Data ({prices.data.length} bars)</CardTitle>
            </CardHeader>
          </div>
          <DataTable<PriceBar>
            columns={[
              { key: 'date', header: 'Date', render: (b) => <span className="font-mono text-xs">{formatDate(b.timestamp)}</span> },
              { key: 'open', header: 'Open', render: (b) => <span className="font-mono text-xs">{formatCurrency(b.open)}</span>, className: 'text-right' },
              { key: 'high', header: 'High', render: (b) => <span className="font-mono text-xs text-[var(--color-positive)]">{formatCurrency(b.high)}</span>, className: 'text-right' },
              { key: 'low', header: 'Low', render: (b) => <span className="font-mono text-xs text-[var(--color-negative)]">{formatCurrency(b.low)}</span>, className: 'text-right' },
              { key: 'close', header: 'Close', render: (b) => <span className="font-mono text-xs font-medium">{formatCurrency(b.close)}</span>, className: 'text-right' },
              { key: 'volume', header: 'Volume', render: (b) => <span className="font-mono text-xs text-[var(--color-text-muted)]">{formatNumber(b.volume, 0)}</span>, className: 'text-right' },
            ]}
            data={prices.data.slice(-50).reverse()}
            keyExtractor={(b) => b.timestamp}
          />
        </Card>
      )}

      {!selectedSymbol && (
        <Card>
          <EmptyState
            title="Select a symbol"
            description="Choose a symbol from the dropdown or ingest new market data to explore."
          />
        </Card>
      )}
    </div>
  );
}
