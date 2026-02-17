import {
  ExternalLink,
  BookmarkMinus,
  Calendar,
  Rss,
  Loader2,
} from "lucide-react";
import type { Article } from "../types/article";

interface BookmarkCardProps {
  article: Article;
  onUnbookmark: (articleId: number) => void;
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

function KeywordBadge({ keyword }: { keyword: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
      {keyword}
    </span>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface ParsedSummary {
  background?: string;
  takeaways?: string[];
  keywords?: string[];
}

function tryParseJson(raw: string): ParsedSummary | null {
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "object" && parsed !== null) return parsed;
  } catch {
    /* not JSON */
  }
  return null;
}

function DetailedSummarySection({
  detailedSummary,
}: {
  detailedSummary: string;
}) {
  const parsed = tryParseJson(detailedSummary);

  if (parsed) {
    return (
      <div className="mt-4 rounded-lg bg-gray-50 p-4 space-y-3">
        {parsed.background && (
          <div>
            <p className="text-sm font-semibold text-gray-700">Background</p>
            <p className="mt-1 text-sm text-gray-600">{parsed.background}</p>
          </div>
        )}
        {parsed.takeaways && parsed.takeaways.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-gray-700">
              Key Takeaways
            </p>
            <ul className="mt-1 space-y-1">
              {parsed.takeaways.map((item, i) => (
                <li
                  key={i}
                  className="text-sm text-gray-600 pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-gray-400"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
        {parsed.keywords && parsed.keywords.length > 0 && (
          <div>
            <p className="text-sm font-semibold text-gray-700">Keywords</p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {parsed.keywords.map((kw) => (
                <KeywordBadge key={kw} keyword={kw} />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Fallback: parse markdown-like format (used by MSW mocks)
  const sections = detailedSummary.split("\n\n").filter(Boolean);

  return (
    <div className="mt-4 rounded-lg bg-gray-50 p-4 space-y-3">
      {sections.map((section, index) => {
        const labelMatch = section.match(/^\*\*(.+?):\*\*\s*([\s\S]*)/);
        if (labelMatch) {
          const [, label, content] = labelMatch;
          const lines = content.split("\n").filter(Boolean);
          const hasBullets = lines.some((line) => line.startsWith("- "));

          if (hasBullets) {
            return (
              <div key={index}>
                <p className="text-sm font-semibold text-gray-700">
                  {label}
                </p>
                <ul className="mt-1 space-y-1">
                  {lines.map((line, i) => (
                    <li
                      key={i}
                      className="text-sm text-gray-600 pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-gray-400"
                    >
                      {line.replace(/^- /, "")}
                    </li>
                  ))}
                </ul>
              </div>
            );
          }

          return (
            <div key={index}>
              <p className="text-sm font-semibold text-gray-700">{label}</p>
              <p className="mt-1 text-sm text-gray-600">{content.trim()}</p>
            </div>
          );
        }

        return (
          <p key={index} className="text-sm text-gray-600">
            {section}
          </p>
        );
      })}
    </div>
  );
}

function SummaryLoadingIndicator() {
  return (
    <div className="mt-4 rounded-lg bg-amber-50 border border-amber-100 p-4 flex items-center gap-3">
      <Loader2 className="h-4 w-4 animate-spin text-amber-500 shrink-0" />
      <p className="text-sm text-amber-700">
        Generating detailed summary...
      </p>
    </div>
  );
}

export default function BookmarkCard({
  article,
  onUnbookmark,
}: BookmarkCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-5 hover:shadow-md transition-shadow border border-gray-100">
      {/* Title */}
      <a
        href={article.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-lg font-semibold text-gray-900 hover:text-indigo-600 transition-colors"
      >
        {article.title}
        <ExternalLink className="h-4 w-4 shrink-0" />
      </a>

      {/* Metadata row */}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-500">
        <span className="inline-flex items-center gap-1">
          <Rss className="h-3.5 w-3.5" />
          {article.source_feed}
        </span>
        {article.published_at && (
          <span className="inline-flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {formatDate(article.published_at)}
          </span>
        )}
        {article.author && <span>by {article.author}</span>}
        {article.relevance_score != null && (
          <ScoreBadge score={article.relevance_score} />
        )}
      </div>

      {/* Keywords */}
      {article.keywords.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {article.keywords.map((kw) => (
            <KeywordBadge key={kw} keyword={kw} />
          ))}
        </div>
      )}

      {/* Basic summary */}
      {article.summary && (
        <p className="mt-3 text-sm text-gray-600">{article.summary}</p>
      )}

      {/* Detailed summary or loading indicator */}
      {article.detailed_summary ? (
        <DetailedSummarySection detailedSummary={article.detailed_summary} />
      ) : (
        <SummaryLoadingIndicator />
      )}

      {/* Unbookmark action */}
      <div className="mt-4 flex items-center">
        <button
          type="button"
          onClick={() => onUnbookmark(article.id)}
          className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm text-amber-500 hover:bg-amber-50 transition-colors"
        >
          <BookmarkMinus className="h-4 w-4" />
          <span>Remove bookmark</span>
        </button>
      </div>
    </div>
  );
}
