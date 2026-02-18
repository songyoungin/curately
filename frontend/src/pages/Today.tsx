import { useMemo } from "react";
import { Newspaper, X } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import DateHeader from "../components/DateHeader";
import ArticleCard from "../components/ArticleCard";
import { ArticleCardSkeleton, ErrorDisplay, EmptyState } from "../components/common";
import { useNewsletter, useArticleInteractions } from "../hooks";

export default function Today() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { newsletter, loading, error, refetch } = useNewsletter();
  const initialArticles = useMemo(
    () => newsletter?.articles ?? [],
    [newsletter],
  );
  const { articles, toggleLike, toggleBookmark } =
    useArticleInteractions(initialArticles);
  const rawArticleFilter = searchParams.get("articles");
  const filterArticleIds = useMemo(() => {
    if (!rawArticleFilter) {
      return null;
    }

    return rawArticleFilter.split(",").map(Number).filter((n) => !Number.isNaN(n));
  }, [rawArticleFilter]);
  const filteredArticles = useMemo(() => {
    if (!filterArticleIds) {
      return articles;
    }

    return articles.filter((article) => filterArticleIds.includes(article.id));
  }, [articles, filterArticleIds]);
  const sortedArticles = useMemo(
    () =>
      [...filteredArticles].sort(
        (a, b) => (b.relevance_score ?? -1) - (a.relevance_score ?? -1),
      ),
    [filteredArticles],
  );

  const handleShowAll = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("articles");
    setSearchParams(nextParams, { replace: true });
  };

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

  return (
    <div>
      <header className="pb-4 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-gray-900">Today</h1>
        <p className="mt-1 text-sm text-gray-600">
          Your curated articles for today.
        </p>
      </header>

      {filterArticleIds && (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-blue-900">
              Showing {sortedArticles.length} articles from Digest
            </p>
            <button
              type="button"
              onClick={handleShowAll}
              className="inline-flex items-center gap-1 rounded-md border border-blue-300 bg-white px-2 py-1 text-sm font-medium text-blue-900 hover:bg-blue-100"
            >
              <X className="h-4 w-4" aria-hidden="true" />
              Show all
            </button>
          </div>
        </div>
      )}
      <div className="mt-6">
        <DateHeader date={newsletter.date} articleCount={sortedArticles.length} />
      </div>
      <div className="mt-6 space-y-4">
        {sortedArticles.map((article) => (
          <ArticleCard
            key={article.id}
            article={article}
            onLike={toggleLike}
            onBookmark={toggleBookmark}
          />
        ))}
      </div>
    </div>
  );
}
