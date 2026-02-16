import { Bookmark } from "lucide-react";

import BookmarkCard from "../components/BookmarkCard";
import { LoadingSpinner, ErrorDisplay, EmptyState } from "../components/common";
import { useBookmarks } from "../hooks";

export default function Bookmarks() {
  const { bookmarks, loading, error, refetch, toggleBookmark } =
    useBookmarks();

  if (loading) {
    return <LoadingSpinner size="lg" message="Loading your bookmarks..." />;
  }

  if (error) {
    return <ErrorDisplay message={error} onRetry={refetch} />;
  }

  if (bookmarks.length === 0) {
    return (
      <EmptyState
        title="No bookmarks yet"
        description="Bookmark articles from the Today page to save them here with detailed summaries."
        icon={<Bookmark className="w-12 h-12" />}
      />
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bookmarks</h1>
          <p className="mt-1 text-sm text-gray-500">
            {bookmarks.length} saved{" "}
            {bookmarks.length === 1 ? "article" : "articles"} with detailed
            summaries
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        {bookmarks.map((article) => (
          <BookmarkCard
            key={article.id}
            article={article}
            onUnbookmark={toggleBookmark}
          />
        ))}
      </div>
    </div>
  );
}
