import { apiClient } from './client';
import type { StrategyInfo, StrategySchemaResponse } from './types';

export const strategiesApi = {
  list: () => apiClient.get<StrategyInfo[]>('/strategies'),

  getSchema: (name: string) =>
    apiClient.get<StrategySchemaResponse>(`/strategies/${name}/schema`),
};
