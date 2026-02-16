import { useState } from 'react';
import { Plus, Trash2, Rss, AlertCircle, Check } from 'lucide-react';

import type { Feed } from '../types';

interface FeedManagerProps {
  feeds: Feed[];
  onAdd: (data: { name: string; url: string }) => Promise<void>;
  onToggle: (id: number, isActive: boolean) => void;
  onRemove: (id: number) => void;
}

function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function FeedManager({
  feeds,
  onAdd,
  onToggle,
  onRemove,
}: FeedManagerProps) {
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [urlError, setUrlError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const handleUrlChange = (value: string) => {
    setUrl(value);
    setSubmitResult(null);
    if (value && !isValidUrl(value)) {
      setUrlError('Please enter a valid URL (http:// or https://)');
    } else {
      setUrlError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url || !name || urlError || submitting) return;

    setSubmitting(true);
    setSubmitResult(null);
    try {
      await onAdd({ name: name.trim(), url: url.trim() });
      setSubmitResult({ type: 'success', message: `Feed "${name}" added successfully` });
      setUrl('');
      setName('');
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (err instanceof Error ? err.message : 'Failed to add feed');
      setSubmitResult({ type: 'error', message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = (id: number) => {
    if (confirmDeleteId === id) {
      onRemove(id);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(id);
    }
  };

  const isSubmitDisabled = !url || !name || !!urlError || submitting;

  return (
    <div>
      {/* Add feed form */}
      <form onSubmit={handleSubmit} className="mb-6 space-y-3">
        <div className="flex gap-3">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Feed name"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <input
            type="text"
            value={url}
            onChange={(e) => handleUrlChange(e.target.value)}
            placeholder="https://example.com/feed"
            className={`flex-[2] rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1 ${
              urlError
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            }`}
          />
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>

        {urlError && (
          <div className="flex items-center gap-1.5 text-sm text-red-600">
            <AlertCircle className="w-3.5 h-3.5" />
            {urlError}
          </div>
        )}

        {submitResult && (
          <div
            className={`flex items-center gap-1.5 text-sm ${
              submitResult.type === 'success' ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {submitResult.type === 'success' ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5" />
            )}
            {submitResult.message}
          </div>
        )}
      </form>

      {/* Feed list */}
      <div className="space-y-2">
        {feeds.map((feed) => (
          <div
            key={feed.id}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Rss
                className={`w-4 h-4 flex-shrink-0 ${
                  feed.is_active ? 'text-orange-500' : 'text-gray-300'
                }`}
              />
              <div className="min-w-0">
                <p
                  className={`text-sm font-medium truncate ${
                    feed.is_active ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {feed.name}
                </p>
                <p className="text-xs text-gray-400 truncate">{feed.url}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 flex-shrink-0 ml-4">
              <span className="text-xs text-gray-400 hidden sm:inline">
                {formatDate(feed.last_fetched_at)}
              </span>

              {/* Toggle switch */}
              <button
                onClick={() => onToggle(feed.id, !feed.is_active)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  feed.is_active ? 'bg-blue-600' : 'bg-gray-300'
                }`}
                aria-label={feed.is_active ? 'Deactivate feed' : 'Activate feed'}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                    feed.is_active ? 'translate-x-4' : 'translate-x-1'
                  }`}
                />
              </button>

              {/* Delete button */}
              <button
                onClick={() => handleDelete(feed.id)}
                onBlur={() => setConfirmDeleteId(null)}
                className={`rounded p-1 transition-colors ${
                  confirmDeleteId === feed.id
                    ? 'bg-red-100 text-red-600'
                    : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                }`}
                aria-label={
                  confirmDeleteId === feed.id
                    ? 'Click again to confirm delete'
                    : 'Delete feed'
                }
                title={
                  confirmDeleteId === feed.id
                    ? 'Click again to confirm'
                    : 'Delete feed'
                }
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
