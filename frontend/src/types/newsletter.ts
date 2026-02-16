import type { Article } from './article';

export interface NewsletterEdition {
  date: string;
  article_count: number;
}

export interface Newsletter {
  date: string;
  articles: Article[];
  categories: string[];
}
