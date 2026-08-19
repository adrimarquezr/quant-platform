import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { backtestsApi } from '@/api/backtests';
import type { BacktestRequest } from '@/api/types';

export function useBacktests() {
  return useQuery({
    queryKey: ['backtests'],
    queryFn: backtestsApi.list,
  });
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: ['backtests', id],
    queryFn: () => backtestsApi.get(id),
    enabled: !!id,
  });
}

export function useRunBacktest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BacktestRequest) => backtestsApi.run(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['backtests'] });
    },
  });
}
