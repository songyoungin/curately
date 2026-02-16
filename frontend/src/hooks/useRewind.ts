import { useState, useEffect, useCallback } from 'react';

import type { RewindReport } from '../types';
import { rewindApi } from '../api/client';

interface UseRewindReturn {
  report: RewindReport | null;
  loading: boolean;
  generating: boolean;
  error: string | null;
  refetch: () => void;
  generate: () => void;
}

export function useRewind(): UseRewindReturn {
  const [report, setReport] = useState<RewindReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLatest = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await rewindApi.getLatest();
      setReport(response.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to load rewind report');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLatest();
  }, [fetchLatest]);

  const generate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = await rewindApi.generate();
      setReport(response.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error
          ? err.message
          : 'Failed to generate rewind report');
      setError(message);
    } finally {
      setGenerating(false);
    }
  }, []);

  return { report, loading, generating, error, refetch: fetchLatest, generate };
}
