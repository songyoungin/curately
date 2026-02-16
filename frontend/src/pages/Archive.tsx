import { useState, useMemo } from "react";
import { Archive as ArchiveIcon, Calendar, List } from "lucide-react";

import type { Article } from "../types";
import CalendarView from "../components/CalendarView";
import DateHeader from "../components/DateHeader";
import CategorySection from "../components/CategorySection";
import {
  ArticleCardSkeleton,
  CalendarSkeleton,
  ErrorDisplay,
  EmptyState,
} from "../components/common";
import {
  useNewsletterEditions,
  useNewsletter,
  useArticleInteractions,
} from "../hooks";

type ViewMode = "calendar" | "list";

export default function Archive() {
  const [viewMode, setViewMode] = useState<ViewMode>("calendar");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const {
    editions,
    loading: editionsLoading,
    error: editionsError,
    refetch: refetchEditions,
  } = useNewsletterEditions();

  const {
    newsletter,
    loading: newsletterLoading,
    error: newsletterError,
    refetch: refetchNewsletter,
  } = useNewsletter(selectedDate ?? undefined);

  const initialArticles = useMemo(
    () => (selectedDate ? newsletter?.articles ?? [] : []),
    [newsletter, selectedDate],
  );
  const { articles, toggleLike, toggleBookmark } =
    useArticleInteractions(initialArticles);

  if (editionsLoading) {
    return (
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-gray-200">
          <div className="animate-pulse">
            <div className="h-7 w-28 rounded bg-gray-200" />
            <div className="h-4 w-52 rounded bg-gray-200 mt-2" />
          </div>
          <div className="animate-pulse flex gap-1 rounded-lg bg-gray-100 p-1">
            <div className="h-8 w-24 rounded-md bg-gray-200" />
            <div className="h-8 w-16 rounded-md bg-gray-200" />
          </div>
        </div>
        <div className="mt-6">
          <CalendarSkeleton />
        </div>
      </div>
    );
  }

  if (editionsError) {
    return <ErrorDisplay message={editionsError} onRetry={refetchEditions} />;
  }

  if (editions.length === 0) {
    return (
      <EmptyState
        title="No newsletters yet"
        description="Newsletters will appear here once the daily pipeline runs."
        icon={<ArchiveIcon className="w-12 h-12" />}
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
      {/* Page header with view toggle */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Archive</h1>
          <p className="mt-1 text-sm text-gray-500">
            Browse past newsletters by date.
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
          <button
            onClick={() => setViewMode("calendar")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === "calendar"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <Calendar className="w-4 h-4" />
            Calendar
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              viewMode === "list"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            <List className="w-4 h-4" />
            List
          </button>
        </div>
      </div>

      <div className="mt-6">
        {/* Calendar view */}
        {viewMode === "calendar" && (
          <CalendarView
            editions={editions}
            selectedDate={selectedDate}
            onSelectDate={setSelectedDate}
          />
        )}

        {/* List view */}
        {viewMode === "list" && (
          <div className="space-y-2">
            {editions.map((edition) => (
              <button
                key={edition.date}
                onClick={() => setSelectedDate(edition.date)}
                className={`w-full flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors ${
                  selectedDate === edition.date
                    ? "border-blue-300 bg-blue-50"
                    : "border-gray-200 bg-white hover:bg-gray-50"
                }`}
              >
                <span className="font-medium text-gray-900">
                  {new Date(edition.date + "T00:00:00").toLocaleDateString(
                    "en-US",
                    {
                      weekday: "short",
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    },
                  )}
                </span>
                <span className="text-sm text-gray-500">
                  {edition.article_count}{" "}
                  {edition.article_count === 1 ? "article" : "articles"}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Selected newsletter display */}
        {selectedDate && (
          <div className="mt-6">
            {newsletterLoading && (
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <ArticleCardSkeleton key={i} />
                ))}
              </div>
            )}

            {newsletterError && (
              <ErrorDisplay
                message={newsletterError}
                onRetry={refetchNewsletter}
              />
            )}

            {!newsletterLoading && !newsletterError && articles.length > 0 && (
              <>
                <DateHeader
                  date={selectedDate}
                  articleCount={articles.length}
                />
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
              </>
            )}

            {!newsletterLoading &&
              !newsletterError &&
              articles.length === 0 && (
                <EmptyState
                  title="No articles found"
                  description="No articles were curated for this date."
                  icon={<ArchiveIcon className="w-12 h-12" />}
                />
              )}
          </div>
        )}

        {/* Prompt to select a date */}
        {!selectedDate && (
          <p className="mt-6 text-center text-sm text-gray-400">
            Select a date to view its newsletter.
          </p>
        )}
      </div>
    </div>
  );
}
