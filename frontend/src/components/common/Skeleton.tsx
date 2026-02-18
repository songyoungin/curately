interface SkeletonProps {
  className?: string;
}

/** Base skeleton block with pulse animation */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded bg-gray-200 ${className}`}
    />
  );
}

/** Mimics the ArticleCard layout: title, source line, summary lines, action buttons */
export function ArticleCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-sm p-5 border border-gray-100">
      {/* Title */}
      <Skeleton className="h-5 w-3/4" />
      {/* Source + score badge */}
      <div className="mt-2 flex items-center gap-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-10 rounded-full" />
      </div>
      {/* Summary lines */}
      <div className="mt-3 space-y-2">
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-5/6" />
        <Skeleton className="h-3.5 w-2/3" />
      </div>
      {/* Action buttons */}
      <div className="mt-4 flex items-center gap-2">
        <Skeleton className="h-8 w-16 rounded-md" />
        <Skeleton className="h-8 w-24 rounded-md" />
      </div>
    </div>
  );
}

/** Mimics the BookmarkCard layout: title, metadata, keywords, summary, detailed section */
export function BookmarkCardSkeleton() {
  return (
    <div className="bg-white rounded-lg shadow-sm p-5 border border-gray-100">
      {/* Title */}
      <Skeleton className="h-5 w-4/5" />
      {/* Metadata row */}
      <div className="mt-2 flex items-center gap-3">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-10 rounded-full" />
      </div>
      {/* Keywords */}
      <div className="mt-3 flex gap-1.5">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-14 rounded-full" />
      </div>
      {/* Summary */}
      <div className="mt-3 space-y-2">
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-4/5" />
      </div>
      {/* Detailed summary section */}
      <div className="mt-4 rounded-lg bg-gray-50 p-4 space-y-3">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-5/6" />
        <Skeleton className="h-4 w-20 mt-2" />
        <Skeleton className="h-3.5 w-full" />
        <Skeleton className="h-3.5 w-3/4" />
      </div>
      {/* Unbookmark button */}
      <div className="mt-4">
        <Skeleton className="h-8 w-36 rounded-md" />
      </div>
    </div>
  );
}

/** Mimics the CalendarView layout: header, weekday labels, day grid */
export function CalendarSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-6">
      {/* Month header */}
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-8 w-8 rounded-lg" />
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      {/* Weekday labels */}
      <div className="grid grid-cols-7 mb-2 gap-1">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-8 mx-auto" />
        ))}
      </div>
      {/* Day grid (5 rows x 7 columns) */}
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: 35 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}

/** Mimics a single feed row in FeedManager */
function FeedItemSkeleton() {
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <Skeleton className="w-4 h-4 rounded-full flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48 mt-1" />
        </div>
      </div>
      <div className="flex items-center gap-3 ml-4">
        <Skeleton className="h-5 w-9 rounded-full" />
        <Skeleton className="h-6 w-6 rounded" />
      </div>
    </div>
  );
}

/** Mimics the FeedManager list */
export function FeedListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <FeedItemSkeleton key={i} />
      ))}
    </div>
  );
}

/** Mimics a single interest bar in InterestProfile */
function InterestItemSkeleton() {
  return (
    <div className="flex items-center gap-3">
      <Skeleton className="w-32 h-4 flex-shrink-0" />
      <Skeleton className="flex-1 h-6 rounded-full" />
      <Skeleton className="w-12 h-4 flex-shrink-0" />
    </div>
  );
}

/** Mimics the InterestProfile list */
export function InterestProfileSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <InterestItemSkeleton key={i} />
      ))}
    </div>
  );
}

/** Mimics the Rewind page layout: header, topic grid, trends list */
export function RewindSkeleton() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-64 mt-2" />
        </div>
        <Skeleton className="h-10 w-32 rounded-lg" />
      </div>
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-8 w-12" />
          </div>
        ))}
      </div>
      {/* Topics grid */}
      <Skeleton className="h-5 w-32 mb-3" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-3">
            <Skeleton className="h-4 w-20 mb-1" />
            <Skeleton className="h-3 w-8" />
          </div>
        ))}
      </div>
      {/* Trends list */}
      <Skeleton className="h-5 w-40 mb-3" />
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full mt-2" />
            <Skeleton className="h-3 w-2/3 mt-1" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function DigestSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="pb-4 border-b border-gray-200">
        <div className="h-7 w-36 rounded bg-gray-200" />
        <div className="h-4 w-48 rounded bg-gray-200 mt-2" />
      </div>
      {/* Headline skeleton */}
      <div className="rounded-xl bg-gray-100 p-6">
        <div className="h-6 w-3/4 rounded bg-gray-200" />
      </div>
      {/* Takeaways skeleton */}
      <div className="rounded-xl bg-gray-100 p-5 space-y-2">
        <div className="h-4 w-24 rounded bg-gray-200" />
        <div className="h-3 w-full rounded bg-gray-200" />
        <div className="h-3 w-5/6 rounded bg-gray-200" />
        <div className="h-3 w-4/6 rounded bg-gray-200" />
      </div>
      {/* Section skeletons (x3) */}
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-xl bg-gray-100 p-5 space-y-3">
          <div className="h-4 w-16 rounded-full bg-gray-200" />
          <div className="h-5 w-2/3 rounded bg-gray-200" />
          <div className="h-3 w-full rounded bg-gray-200" />
          <div className="h-3 w-full rounded bg-gray-200" />
          <div className="h-3 w-3/4 rounded bg-gray-200" />
        </div>
      ))}
    </div>
  );
}
