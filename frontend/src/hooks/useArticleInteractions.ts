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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync state with prop
    setArticles(initialArticles);
  }, [initialArticles]);

  const toggleLike = useCallback((articleId: number) => {
    let snapshot: Article[] = [];
    setArticles((prev) => {
      snapshot = prev;
      return prev.map((a) =>
        a.id === articleId ? { ...a, is_liked: !a.is_liked } : a,
      );
    });

    articlesApi.toggleLike(articleId).catch(() => {
      setArticles(snapshot);
    });
  }, []);

  const toggleBookmark = useCallback((articleId: number) => {
    let snapshot: Article[] = [];
    setArticles((prev) => {
      snapshot = prev;
      return prev.map((a) =>
        a.id === articleId ? { ...a, is_bookmarked: !a.is_bookmarked } : a,
      );
    });

    articlesApi.toggleBookmark(articleId).catch(() => {
      setArticles(snapshot);
    });
  }, []);

  return { articles, toggleLike, toggleBookmark };
}
