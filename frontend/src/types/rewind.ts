export interface HotTopic {
  topic: string;
  count: number;
}

export interface TrendChange {
  keyword: string;
  direction: 'rising' | 'declining';
  weight_change: number;
}

export interface RewindReportContent {
  overview?: string;
  suggestions?: string[];
  [key: string]: unknown;
}

export interface RewindReport {
  id: number;
  user_id: number;
  period_start: string;
  period_end: string;
  report_content: RewindReportContent | null;
  hot_topics: HotTopic[] | string[] | null;
  trend_changes:
    | TrendChange[]
    | {
        rising?: string[];
        declining?: string[];
      }
    | null;
  created_at: string;
}
