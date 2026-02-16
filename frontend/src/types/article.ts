export interface Article {
  id: number;
  source_feed: string;
  source_url: string;
  title: string;
  author: string | null;
  published_at: string | null;
  raw_content: string | null;
  summary: string | null;
  detailed_summary: string | null;
  relevance_score: number | null;
  categories: string[];
  keywords: string[];
  newsletter_date: string | null;
  created_at: string;
  updated_at: string;
  is_liked?: boolean;
  is_bookmarked?: boolean;
}
