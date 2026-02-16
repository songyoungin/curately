import { TrendingUp, TrendingDown } from 'lucide-react';

import type { TrendChange } from '../types/rewind';

interface TrendChartProps {
  trends: TrendChange[];
}

export default function TrendChart({ trends }: TrendChartProps) {
  if (trends.length === 0) return null;

  const maxAbsChange = Math.max(
    ...trends.map((t) => Math.abs(t.weight_change)),
  );

  return (
    <div className="space-y-2" role="list" aria-label="Interest trend changes">
      {trends.map((trend) => {
        const isRising = trend.direction === 'rising';
        const barWidth =
          maxAbsChange > 0
            ? (Math.abs(trend.weight_change) / maxAbsChange) * 100
            : 0;

        return (
          <div key={trend.keyword} className="flex items-center gap-3" role="listitem">
            {/* Icon */}
            {isRising ? (
              <TrendingUp className="h-4 w-4 text-green-500 shrink-0" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-500 shrink-0" />
            )}

            {/* Keyword label */}
            <span className="w-32 text-sm text-gray-700 truncate shrink-0">
              {trend.keyword}
            </span>

            {/* Bar */}
            <div className="flex-1 flex items-center">
              <div className="relative h-6 w-full rounded bg-gray-50">
                <div
                  className={`absolute top-0 h-full rounded transition-all duration-700 ease-out ${
                    isRising ? 'bg-green-100' : 'bg-red-100'
                  }`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>

            {/* Value */}
            <span
              className={`w-12 text-right text-sm font-medium shrink-0 ${
                isRising ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {isRising ? '+' : ''}
              {trend.weight_change.toFixed(1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
