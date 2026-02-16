import { useState, useEffect, useCallback, useRef } from 'react';

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
  const bookmarksRef = useRef<Article[]>([]);

  const fetchBookmarks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await articlesApi.getBookmarked();
      setBookmarks(response.data);
      bookmarksRef.current = response.data;
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
    const snapshot = bookmarksRef.current;
    // Optimistically remove the article from bookmarks
    const updated = snapshot.filter((a) => a.id !== articleId);
    bookmarksRef.current = updated;
    setBookmarks(updated);

    articlesApi.toggleBookmark(articleId).catch(() => {
      bookmarksRef.current = snapshot;
      setBookmarks(snapshot);
    });
  }, []);

  return { bookmarks, loading, error, refetch: fetchBookmarks, toggleBookmark };
}
