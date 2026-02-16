import { useState, useEffect, useCallback } from 'react';

import type { Newsletter } from '../types';
import { newslettersApi } from '../api/client';

interface UseNewsletterReturn {
  newsletter: Newsletter | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useNewsletter(date?: string): UseNewsletterReturn {
  const [newsletter, setNewsletter] = useState<Newsletter | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNewsletter = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = date
        ? await newslettersApi.getByDate(date)
        : await newslettersApi.getToday();
      setNewsletter(response.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to load newsletter');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    fetchNewsletter();
  }, [fetchNewsletter]);

  return { newsletter, loading, error, refetch: fetchNewsletter };
}
