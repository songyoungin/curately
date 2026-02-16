export interface Feed {
  id: number;
  name: string;
  url: string;
  is_active: boolean;
  last_fetched_at: string | null;
  created_at: string;
}

export interface FeedCreate {
  name: string;
  url: string;
}
