import { apiClient } from './client';
import type {
  BacktestRequest,
  BacktestResponse,
  BacktestSummary,
} from './types';

export const backtestsApi = {
  list: () => apiClient.get<BacktestSummary[]>('/backtests'),

  get: (id: string) => apiClient.get<BacktestResponse>(`/backtests/${id}`),

  run: (request: BacktestRequest) =>
    apiClient.post<BacktestResponse>('/backtests', request),

  availableStrategies: () =>
    apiClient.get<string[]>('/backtests/strategies/available'),
};
