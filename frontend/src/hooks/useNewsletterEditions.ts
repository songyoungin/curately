import { useState, useEffect, useCallback } from 'react';

import type { NewsletterEdition } from '../types';
import { newslettersApi } from '../api/client';

interface UseNewsletterEditionsReturn {
  editions: NewsletterEdition[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useNewsletterEditions(): UseNewsletterEditionsReturn {
  const [editions, setEditions] = useState<NewsletterEdition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEditions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await newslettersApi.list();
      setEditions(response.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to load editions');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEditions();
  }, [fetchEditions]);

  return { editions, loading, error, refetch: fetchEditions };
}
