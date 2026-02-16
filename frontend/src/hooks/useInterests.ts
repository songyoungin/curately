import { useState, useEffect, useCallback } from 'react';

import type { UserInterest } from '../types';
import { interestsApi } from '../api/client';

interface UseInterestsReturn {
  interests: UserInterest[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useInterests(): UseInterestsReturn {
  const [interests, setInterests] = useState<UserInterest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInterests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await interestsApi.list();
      const sorted = [...response.data].sort((a, b) => b.weight - a.weight);
      setInterests(sorted);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to load interests');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInterests();
  }, [fetchInterests]);

  return { interests, loading, error, refetch: fetchInterests };
}
