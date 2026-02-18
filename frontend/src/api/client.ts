import axios from 'axios';

import type {
  Article,
  Digest,
  Feed,
  FeedCreate,
  Interaction,
  Newsletter,
  NewsletterEdition,
  RewindReport,
  UserInterest,
} from '../types';
import { supabase } from '../lib/supabase';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
});

// Request interceptor: inject auth token from Supabase session
api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// Articles
export const articlesApi = {
  getById: (id: number) => api.get<Article>(`/articles/${id}`),
  getBookmarked: () => api.get<Article[]>('/articles/bookmarked'),
  toggleLike: (id: number) => api.post<Interaction>(`/articles/${id}/like`),
  toggleBookmark: (id: number) =>
    api.post<Interaction>(`/articles/${id}/bookmark`),
};

// Newsletters
export const newslettersApi = {
  list: () => api.get<NewsletterEdition[]>('/newsletters'),
  getToday: () => api.get<Newsletter>('/newsletters/today'),
  getByDate: (date: string) => api.get<Newsletter>(`/newsletters/${date}`),
};

// Feeds
export const feedsApi = {
  list: () => api.get<Feed[]>('/feeds'),
  create: (data: FeedCreate) => api.post<Feed>('/feeds', data),
  remove: (id: number) => api.delete(`/feeds/${id}`),
  update: (id: number, data: Partial<Feed>) =>
    api.patch<Feed>(`/feeds/${id}`, data),
};

// Interests
export const interestsApi = {
  list: () => api.get<UserInterest[]>('/interests'),
};

// Rewind
export const rewindApi = {
  list: () => api.get<RewindReport[]>('/rewind'),
  getLatest: () => api.get<RewindReport>('/rewind/latest'),
  getById: (id: number) => api.get<RewindReport>(`/rewind/${id}`),
  generate: () => api.post<RewindReport>('/rewind/generate'),
};

// Digests
export const digestApi = {
  getToday: () => api.get<Digest>('/digests/today'),
  getByDate: (date: string) => api.get<Digest>(`/digests/${date}`),
  list: () => api.get<Digest[]>('/digests'),
  generate: () => api.post<Digest>('/digests/generate'),
  generateForDate: (date: string) => api.post<Digest>(`/digests/generate/${date}`),
};

// Pipeline (admin/dev)
export const pipelineApi = {
  run: () => api.post('/pipeline/run'),
};
