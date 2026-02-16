import { ChevronDown, Clock3 } from 'lucide-react';

import type { RewindReport } from '../types';
import { getOverview } from '../lib/rewind';

interface RewindHistoryProps {
  reports: RewindReport[];
  activeReportId: number | null;
  onSelectReport: (report: RewindReport) => void;
}

function formatPeriod(start: string, end: string): string {
  const startDate = new Date(start + 'T00:00:00');
  const endDate = new Date(end + 'T00:00:00');
  return `${startDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
}

export default function RewindHistory({
  reports,
  activeReportId,
  onSelectReport,
}: RewindHistoryProps) {
  if (reports.length === 0) return null;

  return (
    <section className="rounded-xl bg-white border border-gray-200 p-4 sm:p-5">
      <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900">
        <Clock3 className="w-4 h-4 text-gray-500" />
        Rewind History
      </h2>

      <div className="mt-3 space-y-2">
        {reports.map((report) => {
          const isActive = activeReportId === report.id;
          const overview = getOverview(report);
          const summary = overview ?? 'No summary available for this report.';

          return (
            <details
              key={report.id}
              className={`rounded-lg border transition-colors ${isActive ? 'border-blue-300 bg-blue-50/40' : 'border-gray-200 bg-gray-50/40'}`}
              open={isActive}
            >
              <summary
                onClick={() => onSelectReport(report)}
                className="cursor-pointer list-none flex items-center justify-between gap-3 px-3 py-3 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                aria-label={`View rewind report for ${formatPeriod(report.period_start, report.period_end)}`}
              >
                <span className="text-sm font-medium text-gray-900">
                  {formatPeriod(report.period_start, report.period_end)}
                </span>
                <ChevronDown className="w-4 h-4 text-gray-500" />
              </summary>
              <p className="px-3 pb-3 text-sm text-gray-600 leading-relaxed">
                {summary}
              </p>
            </details>
          );
        })}
      </div>
    </section>
  );
}
