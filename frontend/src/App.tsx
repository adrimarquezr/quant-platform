import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from '@/components/layout/AppLayout';

// Pages
import { Dashboard } from '@/pages/Dashboard';
import { DataExplorer } from '@/pages/data/DataExplorer';
import { DataSources } from '@/pages/data/DataSources';
import { StrategyList } from '@/pages/strategies/StrategyList';
import { StrategyDetail } from '@/pages/strategies/StrategyDetail';
import { NewBacktest } from '@/pages/backtesting/NewBacktest';
import { BacktestList } from '@/pages/backtesting/BacktestList';
import { BacktestResults } from '@/pages/backtesting/BacktestResults';
import { PortfolioList } from '@/pages/portfolios/PortfolioList';
import { PortfolioDetail } from '@/pages/portfolios/PortfolioDetail';
import { Settings } from '@/pages/settings/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s before refetch
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            {/* Dashboard */}
            <Route path="/" element={<Dashboard />} />

            {/* Data */}
            <Route path="/data/explorer" element={<DataExplorer />} />
            <Route path="/data/sources" element={<DataSources />} />

            {/* Strategies */}
            <Route path="/strategies" element={<StrategyList />} />
            <Route path="/strategies/:name" element={<StrategyDetail />} />

            {/* Backtesting */}
            <Route path="/backtesting/new" element={<NewBacktest />} />
            <Route path="/backtesting/runs" element={<BacktestList />} />
            <Route path="/backtesting/results/:id" element={<BacktestResults />} />

            {/* Portfolios */}
            <Route path="/portfolios" element={<PortfolioList />} />
            <Route path="/portfolios/:id" element={<PortfolioDetail />} />

            {/* Settings */}
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
