import { useLocation } from 'react-router-dom';

const pathTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/data/explorer': 'Data Explorer',
  '/data/sources': 'Data Sources',
  '/strategies': 'Strategies',
  '/backtesting/new': 'New Backtest',
  '/backtesting/runs': 'Backtest Runs',
  '/portfolios': 'Portfolios',
  '/settings': 'Settings',
};

export function Header() {
  const location = useLocation();

  const title = (() => {
    // Exact match first
    if (pathTitles[location.pathname]) return pathTitles[location.pathname];
    // Pattern match for dynamic routes
    if (location.pathname.startsWith('/backtesting/results/')) return 'Backtest Results';
    if (location.pathname.startsWith('/strategies/')) return 'Strategy Detail';
    if (location.pathname.startsWith('/portfolios/')) return 'Portfolio Detail';
    return 'Quant Platform';
  })();

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--color-border-primary)] bg-[var(--color-bg-secondary)]">
      <h1 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h1>
      <div className="flex items-center gap-3">
        <span className="text-xs text-[var(--color-text-muted)] font-mono">
          v0.2.0
        </span>
      </div>
    </header>
  );
}
