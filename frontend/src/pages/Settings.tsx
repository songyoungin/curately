import { Rss, User, Settings as SettingsIcon } from 'lucide-react';

import { LoadingSpinner, ErrorDisplay } from '../components/common';
import FeedManager from '../components/FeedManager';
import InterestProfile from '../components/InterestProfile';
import { useFeeds, useInterests } from '../hooks';

export default function Settings() {
  const {
    feeds,
    loading: feedsLoading,
    error: feedsError,
    addFeed,
    toggleFeed,
    removeFeed,
    refetch: refetchFeeds,
  } = useFeeds();

  const {
    interests,
    loading: interestsLoading,
    error: interestsError,
    refetch: refetchInterests,
  } = useInterests();

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-2">
          <SettingsIcon className="w-6 h-6 text-gray-700" />
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        </div>
        <p className="mt-1 text-gray-600">
          Manage your feeds and interest profile.
        </p>
      </div>

      {/* Feed Management Section */}
      <section className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <Rss className="w-5 h-5 text-orange-500" />
          <h2 className="text-lg font-semibold text-gray-900">Feed Management</h2>
        </div>

        {feedsLoading ? (
          <LoadingSpinner message="Loading feeds..." />
        ) : feedsError ? (
          <ErrorDisplay message={feedsError} onRetry={refetchFeeds} />
        ) : (
          <FeedManager
            feeds={feeds}
            onAdd={addFeed}
            onToggle={toggleFeed}
            onRemove={removeFeed}
          />
        )}
      </section>

      {/* Interest Profile Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <User className="w-5 h-5 text-blue-500" />
          <h2 className="text-lg font-semibold text-gray-900">Interest Profile</h2>
        </div>

        {interestsLoading ? (
          <LoadingSpinner message="Loading interests..." />
        ) : interestsError ? (
          <ErrorDisplay message={interestsError} onRetry={refetchInterests} />
        ) : (
          <InterestProfile interests={interests} />
        )}
      </section>
    </div>
  );
}
