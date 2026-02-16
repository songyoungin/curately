export type InteractionType = 'like' | 'bookmark';

export interface Interaction {
  id: number;
  user_id: number;
  article_id: number;
  type: InteractionType;
  created_at: string;
}
