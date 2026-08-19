import { apiClient } from './client';
import type { DataQualityReportResponse, DataQualityRunSummary } from './types';

export const dataQualityApi = {
  validate: (symbol: string) =>
    apiClient.post<DataQualityReportResponse>(`/data-quality/validate/${symbol}`),

  listRuns: (params?: { symbol?: string; limit?: number }) =>
    apiClient.get<DataQualityRunSummary[]>('/data-quality', params),

  getRun: (id: string) =>
    apiClient.get<Record<string, unknown>>(`/data-quality/${id}`),
};
