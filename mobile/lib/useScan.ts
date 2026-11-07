import { useMutation } from '@tanstack/react-query';

import { ApiError, scanMessage, type ScanResponse } from '@/lib/api';

/**
 * Scan mutation. gcTime 0 drops the finished mutation (and the message text it holds)
 * from the in-memory cache as soon as nothing observes it; nothing is persisted.
 */
export function useScan() {
  return useMutation<ScanResponse, ApiError, string>({
    mutationFn: scanMessage,
    gcTime: 0,
    retry: false,
  });
}
