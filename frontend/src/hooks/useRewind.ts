import { useState, useEffect, useCallback } from 'react';

import type { RewindReport } from '../types';
import { rewindApi } from '../api/client';

interface UseRewindReturn {
  report: RewindReport | null;
  history: RewindReport[];
  loading: boolean;
  generating: boolean;
  error: string | null;
  refetch: () => void;
  generate: () => Promise<void>;
}

export function useRewind(): UseRewindReturn {
  const [report, setReport] = useState<RewindReport | null>(null);
  const [history, setHistory] = useState<RewindReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRewind = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [latestResponse, historyResponse] = await Promise.all([
        rewindApi.getLatest(),
        rewindApi.list(),
      ]);
      setReport(latestResponse.data);

      const sortedHistory = [...historyResponse.data].sort((a, b) =>
        b.period_end.localeCompare(a.period_end),
      );
      setHistory(sortedHistory);
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
    fetchRewind();
  }, [fetchRewind]);

  const generate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = await rewindApi.generate();
      const generated = response.data;
      setReport(generated);
      setHistory((prev) => {
        const deduped = prev.filter((item) => item.id !== generated.id);
        return [generated, ...deduped];
      });
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

  return {
    report,
    history,
    loading,
    generating,
    error,
    refetch: fetchRewind,
    generate,
  };
}
