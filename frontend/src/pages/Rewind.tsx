import { useMemo, useState } from 'react';
import { Sparkles, RotateCw, TrendingUp } from 'lucide-react';

import RewindHistory from '../components/RewindHistory';
import RewindReport from '../components/RewindReport';
import TrendChart from '../components/TrendChart';
import { EmptyState, ErrorDisplay, RewindSkeleton } from '../components/common';
import { useRewind } from '../hooks';
import { normalizeTrendChanges } from '../lib/rewind';

export default function Rewind() {
  const { report, history, loading, generating, error, refetch, generate } =
    useRewind();
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const activeReportId = selectedReportId ?? report?.id ?? null;

  const activeReport = useMemo(() => {
    if (activeReportId === null) return report;
    return history.find((item) => item.id === activeReportId) ?? report;
  }, [activeReportId, history, report]);

  const trendChanges = activeReport ? normalizeTrendChanges(activeReport) : [];

  if (loading) {
    return <RewindSkeleton />;
  }

  if (error && !report) {
    return <ErrorDisplay message={error} onRetry={refetch} />;
  }

  if (!activeReport) {
    return (
      <EmptyState
        title="No Rewind report yet"
        description="Generate your first weekly rewind to see trend insights."
        icon={<Sparkles className="w-12 h-12" />}
        actionLabel="Generate Rewind"
        onAction={() => void generate()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rewind</h1>
          <p className="mt-1 text-sm text-gray-600">
            Weekly interest trends and reading insights.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void generate()}
          disabled={generating}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
          aria-label="Generate rewind report"
        >
          <RotateCw
            className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          {generating ? 'Generating...' : 'Generate Rewind'}
        </button>
      </div>

      {error && (
        <ErrorDisplay message={error} onRetry={refetch} />
      )}

      <section className="rounded-xl bg-white border border-gray-200 p-4 sm:p-6">
        <RewindReport report={activeReport} />
      </section>

      {trendChanges.length > 0 && (
        <section className="rounded-xl bg-white border border-gray-200 p-4 sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900">
            <TrendingUp className="w-4 h-4 text-green-600" />
            Trend Momentum
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Relative keyword movement for the selected period.
          </p>
          <div className="mt-4">
            <TrendChart trends={trendChanges} />
          </div>
        </section>
      )}

      <RewindHistory
        reports={history}
        activeReportId={activeReport.id}
        onSelectReport={(selected) => setSelectedReportId(selected.id)}
      />
    </div>
  );
}
