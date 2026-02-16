import { useState, useEffect, useCallback } from 'react';

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

  useEffect(() => {
    setArticles(initialArticles);
  }, [initialArticles]);

  const toggleLike = useCallback((articleId: number) => {
    setArticles((prev) => {
      const snapshot = prev;
      const updated = prev.map((a) =>
        a.id === articleId ? { ...a, is_liked: !a.is_liked } : a,
      );

      articlesApi.toggleLike(articleId).catch(() => {
        setArticles(snapshot);
      });

      return updated;
    });
  }, []);

  const toggleBookmark = useCallback((articleId: number) => {
    setArticles((prev) => {
      const snapshot = prev;
      const updated = prev.map((a) =>
        a.id === articleId ? { ...a, is_bookmarked: !a.is_bookmarked } : a,
      );

      articlesApi.toggleBookmark(articleId).catch(() => {
        setArticles(snapshot);
      });

      return updated;
    });
  }, []);

  return { articles, toggleLike, toggleBookmark };
}
