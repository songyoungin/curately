import { useState, useEffect, useCallback, useRef } from 'react';

import type { Article } from '../types';
import { articlesApi } from '../api/client';

interface UseArticleInteractionsReturn {
  articles: Article[];
  toggleLike: (articleId: number) => void;
  toggleBookmark: (articleId: number) => void;
}

export function useArticleInteractions(
  initialArticles: Article[],
): UseArticleInteractionsReturn {
  const [articles, setArticles] = useState<Article[]>(initialArticles);
  const articlesRef = useRef<Article[]>(initialArticles);

  useEffect(() => {
    setArticles(initialArticles);
    articlesRef.current = initialArticles;
  }, [initialArticles]);

  const toggleLike = useCallback((articleId: number) => {
    const snapshot = articlesRef.current;
    const updated = snapshot.map((a) =>
      a.id === articleId ? { ...a, is_liked: !a.is_liked } : a,
    );
    articlesRef.current = updated;
    setArticles(updated);

    articlesApi.toggleLike(articleId).catch(() => {
      articlesRef.current = snapshot;
      setArticles(snapshot);
    });
  }, []);

  const toggleBookmark = useCallback((articleId: number) => {
    const snapshot = articlesRef.current;
    const updated = snapshot.map((a) =>
      a.id === articleId ? { ...a, is_bookmarked: !a.is_bookmarked } : a,
    );
    articlesRef.current = updated;
    setArticles(updated);

    articlesApi.toggleBookmark(articleId).catch(() => {
      articlesRef.current = snapshot;
      setArticles(snapshot);
    });
  }, []);

  return { articles, toggleLike, toggleBookmark };
}
