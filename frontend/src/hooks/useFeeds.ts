import { useState, useEffect, useCallback } from 'react';

import type { Feed, FeedCreate } from '../types';
import { feedsApi } from '../api/client';

interface UseFeedsReturn {
  feeds: Feed[];
  loading: boolean;
  error: string | null;
  addFeed: (data: FeedCreate) => Promise<void>;
  toggleFeed: (id: number, isActive: boolean) => void;
  removeFeed: (id: number) => void;
  refetch: () => void;
}

export function useFeeds(): UseFeedsReturn {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFeeds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await feedsApi.list();
      setFeeds(response.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to load feeds');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeeds();
  }, [fetchFeeds]);

  const addFeed = useCallback(async (data: FeedCreate) => {
    const response = await feedsApi.create(data);
    setFeeds((prev) => [...prev, response.data]);
  }, []);

  const toggleFeed = useCallback((id: number, isActive: boolean) => {
    setFeeds((prev) => {
      const snapshot = prev;
      const updated = prev.map((f) =>
        f.id === id ? { ...f, is_active: isActive } : f,
      );

      feedsApi.update(id, { is_active: isActive }).catch(() => {
        setFeeds(snapshot);
      });

      return updated;
    });
  }, []);

  const removeFeed = useCallback((id: number) => {
    setFeeds((prev) => {
      const snapshot = prev;
      const updated = prev.filter((f) => f.id !== id);

      feedsApi.remove(id).catch(() => {
        setFeeds(snapshot);
      });

      return updated;
    });
  }, []);

  return { feeds, loading, error, addFeed, toggleFeed, removeFeed, refetch: fetchFeeds };
}
