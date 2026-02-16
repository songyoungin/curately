import type { HotTopic, RewindReport, TrendChange } from '../types';

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

export function normalizeHotTopics(report: RewindReport): HotTopic[] {
  const raw = report.hot_topics;
  if (!Array.isArray(raw)) return [];

  if (raw.every((item) => typeof item === 'string')) {
    return (raw as string[]).map((topic) => ({ topic, count: 0 }));
  }

  return raw
    .filter(
      (item): item is HotTopic =>
        typeof item === 'object' &&
        item !== null &&
        typeof (item as HotTopic).topic === 'string' &&
        typeof (item as HotTopic).count === 'number',
    )
    .map((item) => ({ topic: item.topic, count: item.count }));
}

export function normalizeTrendChanges(report: RewindReport): TrendChange[] {
  const raw = report.trend_changes;
  if (!raw) return [];

  if (Array.isArray(raw)) {
    return raw.filter(
      (item): item is TrendChange =>
        typeof item === 'object' &&
        item !== null &&
        typeof (item as TrendChange).keyword === 'string' &&
        ((item as TrendChange).direction === 'rising' ||
          (item as TrendChange).direction === 'declining') &&
        typeof (item as TrendChange).weight_change === 'number',
    );
  }

  const rising = isStringArray(raw.rising) ? raw.rising : [];
  const declining = isStringArray(raw.declining) ? raw.declining : [];

  return [
    ...rising.map((keyword) => ({
      keyword,
      direction: 'rising' as const,
      weight_change: 0,
    })),
    ...declining.map((keyword) => ({
      keyword,
      direction: 'declining' as const,
      weight_change: 0,
    })),
  ];
}

export function getOverview(report: RewindReport): string | null {
  const overview = report.report_content?.overview;
  return typeof overview === 'string' ? overview : null;
}

export function getSuggestions(report: RewindReport): string[] {
  const suggestions = report.report_content?.suggestions;
  return isStringArray(suggestions) ? suggestions : [];
}
