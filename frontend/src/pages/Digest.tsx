import { useState } from 'react'
import { FileText, ChevronLeft, ChevronRight, RotateCw } from 'lucide-react'

import DigestView from '../components/DigestView'
import { EmptyState, ErrorDisplay } from '../components/common'
import { DigestSkeleton } from '../components/common'
import { useDigest } from '../hooks'

/**
 * Shift a YYYY-MM-DD date string by the given number of days.
 * Returns a new YYYY-MM-DD string.
 */
function shiftDate(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().split('T')[0]
}

/** Format YYYY-MM-DD as a human-readable date (e.g., "February 18, 2026"). */
function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export default function Digest() {
  const today = new Date().toISOString().split('T')[0]
  const [selectedDate, setSelectedDate] = useState<string>(today)
  const isToday = selectedDate === today

  // When selectedDate === today, pass undefined to use the /today endpoint
  const { digest, loading, generating, error, notFound, refetch, generate } =
    useDigest(isToday ? undefined : selectedDate)

  const goToPreviousDay = () => setSelectedDate(shiftDate(selectedDate, -1))
  const goToNextDay = () => {
    const next = shiftDate(selectedDate, 1)
    if (next <= today) setSelectedDate(next)
  }

  if (loading) {
    return <DigestSkeleton />
  }

  if (error && !digest) {
    return <ErrorDisplay message={error} onRetry={refetch} />
  }

  if (notFound || !digest) {
    return (
      <div>
        {/* Date navigation even when no digest */}
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-gray-200">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Daily Digest</h1>
            <div className="flex items-center gap-2 mt-1">
              <button
                onClick={goToPreviousDay}
                className="p-1 rounded hover:bg-gray-100"
                aria-label="Previous day"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm text-gray-600">{formatDate(selectedDate)}</span>
              <button
                onClick={goToNextDay}
                disabled={isToday}
                className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"
                aria-label="Next day"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </header>
        <div className="mt-6">
          <EmptyState
            title="No digest yet"
            description={`Digest for ${formatDate(selectedDate)} hasn't been generated yet.`}
            icon={<FileText className="w-12 h-12" />}
            actionLabel={generating ? 'Generating...' : 'Generate Digest'}
            onAction={() => void generate()}
          />
        </div>
      </div>
    )
  }

  return (
    <div>
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily Digest</h1>
          <div className="flex items-center gap-2 mt-1">
            <button
              onClick={goToPreviousDay}
              className="p-1 rounded hover:bg-gray-100 transition-colors"
              aria-label="Previous day"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="text-sm text-gray-600">
              {formatDate(selectedDate)} · {digest.article_count} articles
            </span>
            <button
              onClick={goToNextDay}
              disabled={isToday}
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 transition-colors"
              aria-label="Next day"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void generate()}
          disabled={generating}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
          aria-label="Regenerate digest"
        >
          <RotateCw
            className={`w-4 h-4 ${generating ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          {generating ? 'Generating...' : 'Regenerate'}
        </button>
      </header>

      {error && (
        <div className="mt-4">
          <ErrorDisplay message={error} onRetry={refetch} />
        </div>
      )}

      <div className="mt-6">
        <DigestView digest={digest} />
      </div>
    </div>
  )
}
