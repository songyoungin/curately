import { ExternalLink, ThumbsUp, Bookmark } from "lucide-react";
import type { Article } from "../types/article";

interface ArticleCardProps {
  article: Article;
  onLike: (articleId: number) => void;
  onBookmark: (articleId: number) => void;
}

function ScoreBadge({ score }: { score: number }) {
  let colorClasses: string;
  if (score >= 0.7) {
    colorClasses = "bg-green-100 text-green-700";
  } else if (score >= 0.4) {
    colorClasses = "bg-amber-100 text-amber-700";
  } else {
    colorClasses = "bg-gray-100 text-gray-600";
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClasses}`}
    >
      {score.toFixed(2)}
    </span>
  );
}

export default function ArticleCard({
  article,
  onLike,
  onBookmark,
}: ArticleCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-5 hover:shadow-md transition-shadow border border-gray-100">
      <a
        href={article.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-lg font-semibold text-gray-900 hover:text-indigo-600 transition-colors"
      >
        {article.title}
        <ExternalLink className="h-4 w-4 shrink-0" />
      </a>

      <div className="mt-2 flex items-center gap-2 text-sm text-gray-500">
        <span>{article.source_feed}</span>
        {article.relevance_score != null && (
          <ScoreBadge score={article.relevance_score} />
        )}
      </div>

      {article.summary && (
        <p className="mt-3 text-sm text-gray-600 line-clamp-3">
          {article.summary}
        </p>
      )}

      <div className="mt-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => onLike(article.id)}
          className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
            article.is_liked
              ? "text-indigo-600 bg-indigo-50"
              : "text-gray-400 hover:text-indigo-600 hover:bg-indigo-50"
          }`}
        >
          <ThumbsUp className="h-4 w-4" />
          <span>Like</span>
        </button>

        <button
          type="button"
          onClick={() => onBookmark(article.id)}
          className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
            article.is_bookmarked
              ? "text-amber-500 bg-amber-50"
              : "text-gray-400 hover:text-amber-500 hover:bg-amber-50"
          }`}
        >
          <Bookmark className="h-4 w-4" />
          <span>Bookmark</span>
        </button>
      </div>
    </div>
  );
}
