export interface DigestSection {
  theme: string;
  title: string;
  body: string;
  article_ids: number[];
}

export interface DigestContent {
  headline: string;
  sections: DigestSection[];
  key_takeaways: string[];
  connections: string;
}

export interface Digest {
  id: number;
  digest_date: string;
  content: DigestContent;
  article_ids: number[];
  article_count: number;
  created_at: string;
  updated_at: string;
}
