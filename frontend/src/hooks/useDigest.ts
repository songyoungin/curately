import { useState, useEffect, useCallback } from 'react';

import type { Digest } from '../types';
import { digestApi } from '../api/client';

interface UseDigestReturn {
  digest: Digest | null;
  loading: boolean;
  generating: boolean;
  error: string | null;
  notFound: boolean;
  refetch: () => void;
  generate: () => Promise<void>;
}

export function useDigest(date?: string): UseDigestReturn {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const fetchDigest = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const response = date
        ? await digestApi.getByDate(date)
        : await digestApi.getToday();
      setDigest(response.data);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 404) {
        setNotFound(true);
        setDigest(null);
      } else {
        const message =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ??
          (err instanceof Error ? err.message : 'Failed to load digest');
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    fetchDigest();
  }, [fetchDigest]);

  const generate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = date
        ? await digestApi.generateForDate(date)
        : await digestApi.generate();
      setDigest(response.data);
      setNotFound(false);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to generate digest');
      setError(message);
    } finally {
      setGenerating(false);
    }
  }, [date]);

  return {
    digest,
    loading,
    generating,
    error,
    notFound,
    refetch: fetchDigest,
    generate,
  };
}
