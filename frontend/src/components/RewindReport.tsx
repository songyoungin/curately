import { Flame, TrendingUp, TrendingDown, Calendar } from 'lucide-react';

import type { RewindReport as RewindReportType } from '../types/rewind';
import {
  getOverview,
  getSuggestions,
  normalizeHotTopics,
  normalizeTrendChanges,
} from '../lib/rewind';

interface RewindReportProps {
  report: RewindReportType;
}

function formatPeriod(start: string, end: string): string {
  const startDate = new Date(start + 'T00:00:00');
  const endDate = new Date(end + 'T00:00:00');
  return `${startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
}

function formatCreatedAt(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function HotTopicBadge({ topic, count }: { topic: string; count: number }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-orange-50 border border-orange-100 px-3 py-2">
      <Flame className="h-4 w-4 text-orange-500 shrink-0" />
      <span className="text-sm font-medium text-gray-800">{topic}</span>
      <span className="ml-auto inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">
        {count}
      </span>
    </div>
  );
}

function TrendItem({
  keyword,
  direction,
  weightChange,
}: {
  keyword: string;
  direction: 'rising' | 'declining';
  weightChange: number;
}) {
  const isRising = direction === 'rising';
  return (
    <div className="flex items-center gap-2 py-1.5">
      {isRising ? (
        <TrendingUp className="h-4 w-4 text-green-500 shrink-0" />
      ) : (
        <TrendingDown className="h-4 w-4 text-red-500 shrink-0" />
      )}
      <span className="text-sm text-gray-700">{keyword}</span>
      <span
        className={`ml-auto text-sm font-medium ${isRising ? 'text-green-600' : 'text-red-600'}`}
      >
        {isRising ? '+' : ''}
        {weightChange.toFixed(1)}
      </span>
    </div>
  );
}

export default function RewindReport({ report }: RewindReportProps) {
  const overview = getOverview(report);
  const suggestions = getSuggestions(report);
  const hotTopics = normalizeHotTopics(report);
  const trendChanges = normalizeTrendChanges(report);
  const risingTrends = trendChanges.filter(
    (t) => t.direction === 'rising',
  );
  const decliningTrends = trendChanges.filter(
    (t) => t.direction === 'declining',
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">
          {formatPeriod(report.period_start, report.period_end)}
        </h2>
        <p className="mt-1 flex items-center gap-1 text-sm text-gray-500">
          <Calendar className="h-3.5 w-3.5" />
          Generated {formatCreatedAt(report.created_at)}
        </p>
      </div>

      {/* Overview */}
      {overview && (
        <div className="rounded-lg bg-white shadow-sm border border-gray-100 p-5">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Overview
          </h3>
          <p className="mt-2 text-sm leading-relaxed text-gray-700">
            {overview}
          </p>
        </div>
      )}

      {/* Hot Topics */}
      {hotTopics.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Hot Topics
          </h3>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
            {hotTopics.map((ht) => (
              <HotTopicBadge key={ht.topic} topic={ht.topic} count={ht.count} />
            ))}
          </div>
        </div>
      )}

      {/* Trend Changes */}
      {trendChanges.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Rising */}
          {risingTrends.length > 0 && (
            <div className="rounded-lg bg-white shadow-sm border border-gray-100 p-4">
              <h3 className="flex items-center gap-1.5 text-sm font-semibold text-green-600">
                <TrendingUp className="h-4 w-4" />
                Rising
              </h3>
              <div className="mt-2 divide-y divide-gray-50">
                {risingTrends.map((t) => (
                  <TrendItem
                    key={t.keyword}
                    keyword={t.keyword}
                    direction={t.direction}
                    weightChange={t.weight_change}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Declining */}
          {decliningTrends.length > 0 && (
            <div className="rounded-lg bg-white shadow-sm border border-gray-100 p-4">
              <h3 className="flex items-center gap-1.5 text-sm font-semibold text-red-600">
                <TrendingDown className="h-4 w-4" />
                Declining
              </h3>
              <div className="mt-2 divide-y divide-gray-50">
                {decliningTrends.map((t) => (
                  <TrendItem
                    key={t.keyword}
                    keyword={t.keyword}
                    direction={t.direction}
                    weightChange={t.weight_change}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-4">
          <h3 className="text-sm font-semibold text-indigo-700 uppercase tracking-wide">
            Suggestions For Next Week
          </h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <li
                key={suggestion}
                className="rounded-full bg-white border border-indigo-200 px-3 py-1 text-sm text-indigo-700"
              >
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
