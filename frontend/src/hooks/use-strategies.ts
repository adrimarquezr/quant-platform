import { useQuery } from '@tanstack/react-query';
import { strategiesApi } from '@/api/strategies';

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: strategiesApi.list,
  });
}

export function useStrategySchema(name: string) {
  return useQuery({
    queryKey: ['strategies', name, 'schema'],
    queryFn: () => strategiesApi.getSchema(name),
    enabled: !!name,
  });
}
