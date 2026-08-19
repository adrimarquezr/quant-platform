import { apiClient } from './client';
import type {
  MarketDataRequest,
  MarketDataSummary,
  PriceBar,
} from './types';

export const marketDataApi = {
  ingest: (request: MarketDataRequest) =>
    apiClient.post<MarketDataSummary>('/market-data/ingest', request),

  getPrices: (
    symbol: string,
    params?: { start_date?: string; end_date?: string; limit?: number },
  ) => apiClient.get<PriceBar[]>(`/market-data/prices/${symbol}`, params),

  listSymbols: () => apiClient.get<string[]>('/market-data/symbols'),
};
