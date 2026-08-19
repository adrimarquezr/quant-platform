import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, ApiClientError } from './client';

describe('apiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('performs GET request successfully', async () => {
    const mockData = { status: 'healthy', version: '0.2.0' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await apiClient.get('/health');
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('performs POST request with payload', async () => {
    const payload = { symbol: 'SPY' };
    const mockResponse = { id: '123' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const result = await apiClient.post('/backtests', payload);
    expect(result).toEqual(mockResponse);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/backtests'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    );
  });

  it('throws ApiClientError when response is not ok', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Strategy not found' }),
    } as Response);

    await expect(apiClient.get('/strategies/invalid')).rejects.toThrow(ApiClientError);
  });
});
