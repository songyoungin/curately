import { useState, useEffect, useCallback } from 'react';

import type { Article } from '../types';
import { articlesApi } from '../api/client';

interface UseBookmarksReturn {
  bookmarks: Article[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
  toggleBookmark: (articleId: number) => void;
}

export function useBookmarks(): UseBookmarksReturn {
  const [bookmarks, setBookmarks] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBookmarks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await articlesApi.getBookmarked();
      setBookmarks(response.data);
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to load bookmarks');
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  const toggleBookmark = useCallback((articleId: number) => {
    setBookmarks((prev) => {
      const snapshot = prev;
      // Optimistically remove the article from bookmarks
      const updated = prev.filter((a) => a.id !== articleId);

      articlesApi.toggleBookmark(articleId).catch(() => {
        setBookmarks(snapshot);
      });

      return updated;
    });
  }, []);

  return { bookmarks, loading, error, refetch: fetchBookmarks, toggleBookmark };
}
