import { http, HttpResponse } from 'msw';
import {
  mockArticles,
  mockEditions,
  mockFeeds,
  mockInterests,
  mockRewindReports,
} from './data';

export const handlers = [
  // GET /api/newsletters/today
  http.get('/api/newsletters/today', () => {
    const today = '2026-02-16';
    const articles = mockArticles.filter((a) => a.newsletter_date === today);
    return HttpResponse.json({
      date: today,
      article_count: articles.length,
      articles,
    });
  }),

  // GET /api/newsletters
  http.get('/api/newsletters', () => {
    return HttpResponse.json(mockEditions);
  }),

  // GET /api/newsletters/:date
  http.get('/api/newsletters/:date', ({ params }) => {
    const { date } = params;
    const edition = mockEditions.find((e) => e.date === date);
    if (!edition) {
      return new HttpResponse(null, { status: 404 });
    }
    // Return mock articles adjusted to the requested date
    const articles = mockArticles.slice(0, edition.article_count).map((a) => ({
      ...a,
      newsletter_date: date as string,
    }));
    return HttpResponse.json({
      date,
      article_count: articles.length,
      articles,
    });
  }),

  // GET /api/articles/bookmarked (must be before /api/articles/:id to avoid route conflict)
  http.get('/api/articles/bookmarked', () => {
    return HttpResponse.json(mockArticles.filter((a) => a.is_bookmarked));
  }),

  // GET /api/articles/:id
  http.get('/api/articles/:id', ({ params }) => {
    const article = mockArticles.find((a) => a.id === Number(params.id));
    if (!article) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(article);
  }),

  // POST /api/articles/:id/like (toggle)
  http.post('/api/articles/:id/like', ({ params }) => {
    const article = mockArticles.find((a) => a.id === Number(params.id));
    if (!article) {
      return new HttpResponse(null, { status: 404 });
    }
    article.is_liked = !article.is_liked;
    return HttpResponse.json({
      article_id: article.id,
      type: 'like',
      active: article.is_liked,
      created_at: article.is_liked ? new Date().toISOString() : null,
    });
  }),

  // POST /api/articles/:id/bookmark (toggle)
  http.post('/api/articles/:id/bookmark', ({ params }) => {
    const article = mockArticles.find((a) => a.id === Number(params.id));
    if (!article) {
      return new HttpResponse(null, { status: 404 });
    }
    article.is_bookmarked = !article.is_bookmarked;
    return HttpResponse.json({
      article_id: article.id,
      type: 'bookmark',
      active: article.is_bookmarked,
      created_at: article.is_bookmarked ? new Date().toISOString() : null,
    });
  }),

  // GET /api/feeds
  http.get('/api/feeds', () => {
    return HttpResponse.json(mockFeeds);
  }),

  // POST /api/feeds
  http.post('/api/feeds', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newFeed = {
      id: mockFeeds.length + 1,
      ...body,
      is_active: true,
      last_fetched_at: null,
      created_at: new Date().toISOString(),
    };
    return HttpResponse.json(newFeed, { status: 201 });
  }),

  // DELETE /api/feeds/:id
  http.delete('/api/feeds/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // PATCH /api/feeds/:id
  http.patch('/api/feeds/:id', async ({ params, request }) => {
    const feed = mockFeeds.find((f) => f.id === Number(params.id));
    if (!feed) {
      return new HttpResponse(null, { status: 404 });
    }
    const body = (await request.json()) as Record<string, unknown>;
    const updated = { ...feed, ...body };
    return HttpResponse.json(updated);
  }),

  // GET /api/interests
  http.get('/api/interests', () => {
    return HttpResponse.json(mockInterests);
  }),

  // GET /api/rewind/latest (must be before /api/rewind/:id to avoid route conflict)
  http.get('/api/rewind/latest', () => {
    return HttpResponse.json(mockRewindReports[0]);
  }),

  // GET /api/rewind (list all reports)
  http.get('/api/rewind', () => {
    return HttpResponse.json(mockRewindReports);
  }),

  // GET /api/rewind/:id
  http.get('/api/rewind/:id', ({ params }) => {
    const report = mockRewindReports.find(
      (r) => r.id === Number(params.id),
    );
    if (!report) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(report);
  }),

  // POST /api/rewind/generate
  http.post('/api/rewind/generate', () => {
    return HttpResponse.json(mockRewindReports[0], { status: 201 });
  }),

  // POST /api/pipeline/run
  http.post('/api/pipeline/run', () => {
    return HttpResponse.json({ status: 'started' });
  }),

  // GET /api/health
  http.get('/api/health', () => {
    return HttpResponse.json({ status: 'ok' });
  }),
];
