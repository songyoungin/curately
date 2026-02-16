export interface HotTopic {
  topic: string;
  count: number;
}

export interface TrendChange {
  keyword: string;
  direction: 'rising' | 'declining';
  weight_change: number;
}

export interface RewindReport {
  id: number;
  user_id: number;
  period_start: string;
  period_end: string;
  report_content: Record<string, unknown> | null;
  hot_topics: HotTopic[];
  trend_changes: TrendChange[];
  created_at: string;
}
