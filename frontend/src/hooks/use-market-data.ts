import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { marketDataApi } from '@/api/market-data';
import type { MarketDataRequest } from '@/api/types';

export function useSymbols() {
  return useQuery({
    queryKey: ['market-data', 'symbols'],
    queryFn: marketDataApi.listSymbols,
  });
}

export function usePrices(
  symbol: string,
  params?: { start_date?: string; end_date?: string; limit?: number },
) {
  return useQuery({
    queryKey: ['market-data', 'prices', symbol, params],
    queryFn: () => marketDataApi.getPrices(symbol, params),
    enabled: !!symbol,
  });
}

export function useIngestData() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: MarketDataRequest) => marketDataApi.ingest(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['market-data'] });
    },
  });
}
