import { useQuery } from '@tanstack/react-query';
import { healthApi } from '@/api/health';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 30_000, // Poll every 30s
    retry: 1,
  });
}
