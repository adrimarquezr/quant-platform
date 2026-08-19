import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Play, Settings } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/States';
import { useStrategies, useStrategySchema } from '@/hooks/use-strategies';
import { useRunBacktest } from '@/hooks/use-backtests';
import { DEFAULT_UNIVERSE } from '@/lib/constants';
import type { BacktestRequest } from '@/api/types';

export function NewBacktest() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const strategies = useStrategies();
  const runBacktest = useRunBacktest();

  const [form, setForm] = useState<BacktestRequest>({
    strategy_name: searchParams.get('strategy') ?? '',
    parameters: {},
    universe: DEFAULT_UNIVERSE,
    start_date: '2020-01-01',
    end_date: '2024-01-01',
    initial_cash: 100_000,
    commission_rate_bps: 5,
    slippage_rate_bps: 5,
    frequency: '1d',
  });

  const [universeInput, setUniverseInput] = useState(DEFAULT_UNIVERSE.join(', '));

  const schema = useStrategySchema(form.strategy_name);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runBacktest.mutate(
      { ...form, universe: universeInput.split(',').map((s) => s.trim()).filter(Boolean) },
      {
        onSuccess: (result) => navigate(`/backtesting/results/${result.id}`),
      },
    );
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4 animate-fade-in">
      <Card accent>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2">
              <Play className="w-4 h-4" />
              Configure Backtest
            </span>
          </CardTitle>
        </CardHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Strategy Selection */}
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">Strategy</label>
            {strategies.isLoading ? (
              <LoadingState />
            ) : (
              <select
                value={form.strategy_name}
                onChange={(e) => setForm((f) => ({ ...f, strategy_name: e.target.value, parameters: {} }))}
                required
                className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-border-accent)]"
              >
                <option value="">Select strategy...</option>
                {strategies.data?.map((s) => (
                  <option key={s.name} value={s.name}>{s.name} (v{s.version})</option>
                ))}
              </select>
            )}
          </div>

          {/* Strategy Parameters */}
          {schema.data && Object.keys(schema.data.parameters).length > 0 && (
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">
                <span className="flex items-center gap-1"><Settings className="w-3 h-3" /> Parameters</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(schema.data.parameters).map(([key, param]) => (
                  <div key={key}>
                    <label className="block text-xs text-[var(--color-text-secondary)] mb-1">{key}</label>
                    <input
                      type="number"
                      step="any"
                      min={param.min}
                      max={param.max}
                      value={(form.parameters?.[key] as number) ?? param.default}
                      onChange={(e) => setForm((f) => ({
                        ...f,
                        parameters: { ...(f.parameters ?? {}), [key]: Number(e.target.value) },
                      }))}
                      className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono outline-none focus:border-[var(--color-border-accent)]"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Universe */}
          <div>
            <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">Universe (comma-separated)</label>
            <input
              type="text"
              value={universeInput}
              onChange={(e) => setUniverseInput(e.target.value)}
              className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono outline-none focus:border-[var(--color-border-accent)]"
            />
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">Start Date</label>
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-border-accent)]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">End Date</label>
              <input
                type="date"
                value={form.end_date}
                onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-border-accent)]"
              />
            </div>
          </div>

          {/* Capital & Costs */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">Initial Cash</label>
              <input
                type="number"
                value={form.initial_cash}
                onChange={(e) => setForm((f) => ({ ...f, initial_cash: Number(e.target.value) }))}
                className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono outline-none focus:border-[var(--color-border-accent)]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">Commission (bps)</label>
              <input
                type="number"
                step="0.1"
                value={form.commission_rate_bps}
                onChange={(e) => setForm((f) => ({ ...f, commission_rate_bps: Number(e.target.value) }))}
                className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono outline-none focus:border-[var(--color-border-accent)]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase mb-1.5">Slippage (bps)</label>
              <input
                type="number"
                step="0.1"
                value={form.slippage_rate_bps}
                onChange={(e) => setForm((f) => ({ ...f, slippage_rate_bps: Number(e.target.value) }))}
                className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border-secondary)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-primary)] font-mono outline-none focus:border-[var(--color-border-accent)]"
              />
            </div>
          </div>

          {/* Submit */}
          <div className="pt-2">
            <Button type="submit" size="lg" className="w-full" loading={runBacktest.isPending}>
              <Play className="w-4 h-4" />
              Run Backtest
            </Button>
          </div>

          {runBacktest.isError && (
            <p className="text-xs text-[var(--color-negative)]">
              Backtest failed: {runBacktest.error.message}
            </p>
          )}
        </form>
      </Card>
    </div>
  );
}
