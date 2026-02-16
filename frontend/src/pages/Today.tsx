import { Newspaper } from "lucide-react";

import type { Article } from "../types";
import DateHeader from "../components/DateHeader";
import CategorySection from "../components/CategorySection";
import { LoadingSpinner, ErrorDisplay, EmptyState } from "../components/common";
import { useNewsletter, useArticleInteractions } from "../hooks";

export default function Today() {
  const { newsletter, loading, error, refetch } = useNewsletter();
  const { articles, toggleLike, toggleBookmark } = useArticleInteractions(
    newsletter?.articles ?? [],
  );

  if (loading) {
    return <LoadingSpinner size="lg" message="Loading today's newsletter..." />;
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
