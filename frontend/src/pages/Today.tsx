import { useMemo } from "react";
import { Newspaper } from "lucide-react";

import type { Article } from "../types";
import DateHeader from "../components/DateHeader";
import CategorySection from "../components/CategorySection";
import { ArticleCardSkeleton, ErrorDisplay, EmptyState } from "../components/common";
import { useNewsletter, useArticleInteractions } from "../hooks";

export default function Today() {
  const { newsletter, loading, error, refetch } = useNewsletter();
  const initialArticles = useMemo(
    () => newsletter?.articles ?? [],
    [newsletter],
  );
  const { articles, toggleLike, toggleBookmark } =
    useArticleInteractions(initialArticles);

  if (loading) {
    return (
      <div>
        {/* Skeleton date header */}
        <div className="flex items-center justify-between">
          <div className="animate-pulse">
            <div className="h-7 w-48 rounded bg-gray-200" />
            <div className="h-4 w-24 rounded bg-gray-200 mt-2" />
          </div>
        </div>
        {/* Skeleton article cards */}
        <div className="mt-6 space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <ArticleCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorDisplay message={error} onRetry={refetch} />;
  }

  if (!newsletter || articles.length === 0) {
    return (
      <EmptyState
        title="No articles today"
        description="Check back later — new articles are curated every morning."
        icon={<Newspaper className="w-12 h-12" />}
      />
    );
  }

  const articlesByCategory: Record<string, Article[]> = {};
  for (const article of articles) {
    const category = article.categories[0] || "Uncategorized";
    if (!articlesByCategory[category]) {
      articlesByCategory[category] = [];
    }
    articlesByCategory[category].push(article);
  }

  const sortedCategories = Object.keys(articlesByCategory).sort();

  return (
    <div>
      <DateHeader date={newsletter.date} articleCount={articles.length} />
      <div className="mt-6">
        {sortedCategories.map((category) => (
          <CategorySection
            key={category}
            category={category}
            articles={articlesByCategory[category]}
            onLike={toggleLike}
            onBookmark={toggleBookmark}
          />
        ))}
      </div>
    </div>
  );
}
