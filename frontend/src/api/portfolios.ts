import { apiClient } from './client';
import type {
  PortfolioCreateRequest,
  PortfolioPerformanceResponse,
  PortfolioSummary,
  PositionResponse,
} from './types';

export const portfoliosApi = {
  list: (limit?: number) =>
    apiClient.get<PortfolioSummary[]>('/portfolios', { limit }),

  get: (id: string) =>
    apiClient.get<PortfolioSummary>(`/portfolios/${id}`),

  create: (request: PortfolioCreateRequest) =>
    apiClient.post<PortfolioSummary>('/portfolios', request),

  getPositions: (id: string) =>
    apiClient.get<PositionResponse[]>(`/portfolios/${id}/positions`),

  getPerformance: (id: string, limit?: number) =>
    apiClient.get<PortfolioPerformanceResponse>(
      `/portfolios/${id}/performance`,
      { limit },
    ),
};
