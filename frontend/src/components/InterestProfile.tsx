import { TrendingUp } from 'lucide-react';

import type { UserInterest } from '../types';

interface InterestProfileProps {
  interests: UserInterest[];
}

export default function InterestProfile({ interests }: InterestProfileProps) {
  if (interests.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No interests tracked yet. Like some articles to build your profile!
      </p>
    );
  }

  const maxWeight = Math.max(...interests.map((i) => i.weight));

  return (
    <div className="space-y-3">
      {interests.map((interest) => {
        const percentage = maxWeight > 0 ? (interest.weight / maxWeight) * 100 : 0;

        return (
          <div key={interest.id} className="flex items-center gap-3">
            <span className="w-32 text-sm font-medium text-gray-700 truncate flex-shrink-0">
              {interest.keyword}
            </span>
            <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <span className="w-12 text-right text-sm text-gray-500 flex-shrink-0">
              {interest.weight.toFixed(1)}
            </span>
          </div>
        );
      })}

      <div className="flex items-center gap-1.5 mt-4 pt-3 border-t border-gray-100">
        <TrendingUp className="w-3.5 h-3.5 text-gray-400" />
        <p className="text-xs text-gray-400">
          Weights increase when you like related articles
        </p>
      </div>
    </div>
  );
}
