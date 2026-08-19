import { useQuery } from '@tanstack/react-query';
import { portfoliosApi } from '@/api/portfolios';

export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfoliosApi.list(),
  });
}

export function usePortfolio(id: string) {
  return useQuery({
    queryKey: ['portfolios', id],
    queryFn: () => portfoliosApi.get(id),
    enabled: !!id,
  });
}

export function usePortfolioPositions(id: string) {
  return useQuery({
    queryKey: ['portfolios', id, 'positions'],
    queryFn: () => portfoliosApi.getPositions(id),
    enabled: !!id,
  });
}

export function usePortfolioPerformance(id: string) {
  return useQuery({
    queryKey: ['portfolios', id, 'performance'],
    queryFn: () => portfoliosApi.getPerformance(id),
    enabled: !!id,
  });
}
