export interface UserInterest {
  id: number;
  user_id: number;
  keyword: string;
  weight: number;
  source: string | null;
  updated_at: string;
}
