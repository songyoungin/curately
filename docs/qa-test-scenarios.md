# QA Test Scenarios — Playwright MCP Browser Testing

> **Tool**: Playwright MCP (real browser interaction)
> **Pre-requisite**: Both backend and frontend running (see Environment Setup)

---

## Table of Contents

### Part A: Backend Pipeline (Real Data)

1. [Test Environment Setup](#1-test-environment-setup)
2. [TC-PIPE: Daily Pipeline E2E](#2-tc-pipe-daily-pipeline-e2e)
3. [TC-FEED: RSS Feed Collection](#3-tc-feed-rss-feed-collection)
4. [TC-SCORE: AI Scoring & Filtering](#4-tc-score-ai-scoring--filtering)
5. [TC-SUMMARY: Summary Generation](#5-tc-summary-summary-generation)
6. [TC-FEEDBACK: Feedback Loop (Like → Interests)](#6-tc-feedback-feedback-loop-like--interests)
7. [TC-RWGEN: Rewind Report Generation](#7-tc-rwgen-rewind-report-generation)

### Part B: Frontend UI

8. [TC-NAV: Navigation](#8-tc-nav-navigation)
9. [TC-TODAY: Today Page](#9-tc-today-today-page)
10. [TC-ARCHIVE: Archive Page](#10-tc-archive-archive-page)
11. [TC-BOOKMARKS: Bookmarks Page](#11-tc-bookmarks-bookmarks-page)
12. [TC-REWIND: Rewind Page](#12-tc-rewind-rewind-page)
13. [TC-SETTINGS: Settings Page](#13-tc-settings-settings-page)
14. [TC-CROSS: Cross-Page Interactions](#14-tc-cross-cross-page-interactions)
15. [TC-RESPONSIVE: Responsive Design](#15-tc-responsive-responsive-design)
16. [TC-A11Y: Accessibility](#16-tc-a11y-accessibility)
17. [TC-VISUAL: Visual & UX Polish](#17-tc-visual-visual--ux-polish)

### Part C: Full Integration

18. [TC-E2E: End-to-End Integration](#18-tc-e2e-end-to-end-integration)

---

## 1. Test Environment Setup

### Full-stack environment (Parts A, B, C)

```bash
# Terminal 1: Backend
uv run uvicorn backend.main:app --reload
# Backend starts at http://localhost:8000

# Terminal 2: Frontend (proxies /api to backend)
cd frontend && npm run dev
# Frontend starts at http://localhost:5173
```

**Required services**:
- Supabase project running (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY in `.env`)
- Gemini API key configured (GEMINI_API_KEY in `.env`)
- Default user seeded (auto-created on backend startup: `default@curately.local`)

### Environment verification

| Step | Action | Expected |
|------|--------|----------|
| 1 | `browser_navigate` to `http://localhost:5173` | Frontend loads |
| 2 | `browser_navigate` to `http://localhost:8000/api/health` | `{"status": "ok"}` |
| 3 | Check `browser_console_messages` on frontend | No errors |

---

# Part A: Backend Pipeline (Real Data)

---

## 2. TC-PIPE: Daily Pipeline E2E

> Tests the full daily pipeline: RSS collection → AI scoring → filtering → summarization → DB persistence.
> Trigger via `POST /api/pipeline/run` and verify results through API and UI.

### TC-PIPE-01: Trigger pipeline and verify result

| Step | Action | Expected |
|------|--------|----------|
| 1 | `browser_navigate` to `http://localhost:8000/api/health` | `{"status": "ok"}` — backend alive |
| 2 | Execute via browser console or API: `POST /api/pipeline/run` | Returns `PipelineResult` JSON |
| 3 | Verify `articles_collected` > 0 | RSS feeds fetched successfully |
| 4 | Verify `articles_scored` > 0 | Gemini scoring executed |
| 5 | Verify `articles_filtered` > 0 | Relevance filter applied (threshold ≥ 0.3) |
| 6 | Verify `articles_summarized` > 0 | Korean summaries generated |
| 7 | Verify `newsletter_date` = today's date (YYYY-MM-DD) | Date correctly assigned |
| 8 | Verify `articles_filtered` ≤ 20 | Max articles per newsletter enforced |

### TC-PIPE-02: Pipeline idempotency (deduplication)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Run pipeline: `POST /api/pipeline/run` | Note `articles_collected` count (first run) |
| 2 | Run pipeline again immediately | `articles_collected` ≤ first run count |
| 3 | Compare results | Second run collects fewer or zero new articles (dedup by `source_url`) |

### TC-PIPE-03: Pipeline result accessible via newsletter API

| Step | Action | Expected |
|------|--------|----------|
| 1 | After pipeline run, `GET /api/newsletters/today` | Returns newsletter with articles |
| 2 | Verify `articles` array is non-empty | Articles from pipeline are served |
| 3 | Each article has `title`, `summary`, `relevance_score` | Pipeline output fields present |
| 4 | Articles sorted by `relevance_score` descending | Highest relevance first |

### TC-PIPE-04: Pipeline resilience — partial feed failure

| Step | Action | Expected |
|------|--------|----------|
| 1 | (If possible) Temporarily add an invalid feed URL in Settings | Invalid feed added |
| 2 | Run pipeline: `POST /api/pipeline/run` | Pipeline completes without crashing |
| 3 | `articles_collected` > 0 | Valid feeds still collected |
| 4 | Check backend logs | Warning logged for failed feed, no stack trace crash |

---

## 3. TC-FEED: RSS Feed Collection

> Verifies RSS feeds are fetched, parsed, and deduplicated correctly.

### TC-FEED-01: Active feeds are collected

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Settings page `http://localhost:5173/settings` | Feed list displayed |
| 2 | Note which feeds are active (green indicator) | e.g., Hacker News, TechCrunch, The Verge, Ars Technica, MIT Tech Review |
| 3 | Run pipeline | `articles_collected` count reflects articles from active feeds |
| 4 | Navigate to Today page | Articles show `source` matching active feed names |

### TC-FEED-02: Inactive feeds are skipped

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Settings page, disable a feed (e.g., TechCrunch) | Feed toggle turns inactive |
| 2 | Run pipeline | No new articles from disabled feed |
| 3 | Re-enable the feed | Feed toggle turns active |

### TC-FEED-03: New feed added and collected

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Settings page, add a new feed (name: "Python Blog", URL: valid RSS) | Feed appears in list |
| 2 | Run pipeline | New feed's articles appear in `articles_collected` |
| 3 | Navigate to Today page | Articles from new feed visible with correct source name |

### TC-FEED-04: Feed deletion stops collection

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Settings page, delete a feed | Feed removed from list |
| 2 | Run pipeline | No articles collected from deleted feed |

### TC-FEED-05: Article deduplication across feeds

| Step | Action | Expected |
|------|--------|----------|
| 1 | Run pipeline | Note articles collected |
| 2 | Check Today page | No duplicate article titles from overlapping feeds |
| 3 | Run pipeline again | Second run doesn't re-insert same `source_url` articles |

---

## 4. TC-SCORE: AI Scoring & Filtering

> Verifies Gemini scores articles against user interests, and filtering works correctly.

### TC-SCORE-01: Articles have valid relevance scores

| Step | Action | Expected |
|------|--------|----------|
| 1 | After pipeline run, navigate to Today page | Articles displayed |
| 2 | Inspect relevance score badges on each article | All scores between 0.0 and 1.0 |
| 3 | No article has score below 0.3 | Filter threshold applied |

### TC-SCORE-02: Articles have categories and keywords

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, verify category sections | Articles grouped by categories (e.g., AI/ML, Backend) |
| 2 | Inspect an article via `GET /api/articles/{id}` | Response includes `categories` array (2-3 items) |
| 3 | Response includes `keywords` array | 3-5 technical keywords per article |

### TC-SCORE-03: Scoring reflects user interests

| Step | Action | Expected |
|------|--------|----------|
| 1 | Check interests via `GET /api/interests` | Current interest keywords and weights |
| 2 | Check Today's articles | Higher-scored articles align with top-weighted interests |
| 3 | Articles matching top interests (e.g., "machine-learning" weight 5.2) | Tend to have higher relevance scores |

### TC-SCORE-04: Max 20 articles per newsletter

| Step | Action | Expected |
|------|--------|----------|
| 1 | After pipeline run, `GET /api/newsletters/today` | Response has `articles` array |
| 2 | Count articles | ≤ 20 articles |
| 3 | All articles have `relevance_score` ≥ 0.3 | Threshold enforced |

---

## 5. TC-SUMMARY: Summary Generation

> Verifies both basic (pipeline) and detailed (bookmark) summaries.

### TC-SUMMARY-01: Basic summaries are Korean

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Today page | Articles with summaries visible |
| 2 | Inspect summary text | Written in Korean |
| 3 | Summary length | 2-3 sentences, concise |
| 4 | Summary content | Relates to the article title/topic |

### TC-SUMMARY-02: Detailed summary on bookmark

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, bookmark an article that is not yet bookmarked | Bookmark button becomes active |
| 2 | Wait 5-10 seconds (Gemini async generation) | Background task completes |
| 3 | Navigate to Bookmarks page | Bookmarked article appears |
| 4 | Verify detailed summary structure | Has "Background", "Key Takeaways", "Keywords" sections |
| 5 | "Background" section | Korean contextual paragraph |
| 6 | "Key Takeaways" section | 3-5 bullet points in Korean |
| 7 | "Keywords" section | Technical keyword badges |

### TC-SUMMARY-03: Detailed summary persists after unbookmark/re-bookmark

| Step | Action | Expected |
|------|--------|----------|
| 1 | Bookmark an article, wait for detailed summary | Detailed summary generated |
| 2 | Unbookmark the article | Removed from Bookmarks page |
| 3 | Re-bookmark the same article | Article reappears in Bookmarks |
| 4 | Detailed summary still present | Previous detailed summary preserved (not regenerated) |

---

## 6. TC-FEEDBACK: Feedback Loop (Like → Interests)

> Verifies that liking articles updates user interest weights and influences future scoring.

### TC-FEEDBACK-01: Like increases interest weights

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Settings, note current interest weights | Record weights (e.g., "kubernetes": 3.0) |
| 2 | Navigate to Today page | Articles displayed |
| 3 | Find and like an article with "kubernetes" keyword | Like button active |
| 4 | Navigate back to Settings → interests section | Page loads |
| 5 | Check "kubernetes" weight | Increased by 1.0 (now 4.0) |

### TC-FEEDBACK-02: Unlike decreases interest weights

| Step | Action | Expected |
|------|--------|----------|
| 1 | Note current weight for a keyword (e.g., "kubernetes": 4.0) | Weight recorded |
| 2 | Navigate to Today page, find the previously liked article | Like button active |
| 3 | Click like button to unlike | Like button returns to inactive |
| 4 | Navigate to Settings → interests | Page loads |
| 5 | Check "kubernetes" weight | Decreased by 1.0 (back to 3.0) |

### TC-FEEDBACK-03: New interest keyword created on like

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Settings, note all interest keywords | List recorded |
| 2 | Navigate to Today page | Articles displayed |
| 3 | Like an article with a keyword not in current interests | Like button active |
| 4 | Navigate to Settings → interests | Page loads |
| 5 | New keyword appears in interest list | Weight = 1.0 |

### TC-FEEDBACK-04: Interest weight influences next pipeline scoring

| Step | Action | Expected |
|------|--------|----------|
| 1 | Like several articles about a specific topic (e.g., "kubernetes") | Multiple likes |
| 2 | Verify interest weight increased significantly | Weight > original |
| 3 | Run pipeline: `POST /api/pipeline/run` | New articles scored |
| 4 | Check Today page | Kubernetes-related articles tend to have higher scores than before |

### TC-FEEDBACK-05: Interest bar chart updates in real time

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Settings page, note bar widths | Bars proportional to weights |
| 2 | Navigate to Today page, like articles for a low-weight interest | Likes registered |
| 3 | Return to Settings page | Interest bars re-render |
| 4 | The liked interest's bar is now wider | Visual update reflects weight increase |

---

## 7. TC-RWGEN: Rewind Report Generation

> Verifies weekly Rewind report generation with real Gemini analysis.

### TC-RWGEN-01: Generate Rewind with liked articles

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ensure ≥ 5 articles are liked (like on Today page if needed) | Multiple likes registered |
| 2 | Navigate to Rewind page | Page loads |
| 3 | Click "Generate Rewind" button | Loading state appears |
| 4 | Wait for generation (may take 10-30s for Gemini) | Loading resolves |
| 5 | Report displays with period dates | Period covers the past 7 days |

### TC-RWGEN-02: Hot Topics reflect liked articles

| Step | Action | Expected |
|------|--------|----------|
| 1 | After generating Rewind report | Hot Topics section visible |
| 2 | Topics match categories of liked articles | e.g., liked AI articles → "AI/ML" in hot topics |
| 3 | Topic counts are reasonable | Count ≤ number of liked articles |

### TC-RWGEN-03: Trend Changes section

| Step | Action | Expected |
|------|--------|----------|
| 1 | Inspect "Rising" trends | Topics with increased engagement this week |
| 2 | Inspect "Declining" trends | Topics absent or decreased this week |
| 3 | Trends make sense relative to liked articles | Not contradictory |

### TC-RWGEN-04: Suggestions are actionable

| Step | Action | Expected |
|------|--------|----------|
| 1 | Inspect Suggestions section | 2-4 keyword suggestions listed |
| 2 | Suggestions are relevant to user's interests | Related to current hot topics |
| 3 | Suggestions are not already top-weighted interests | Suggest expansion, not repetition |

### TC-RWGEN-05: Rewind history accumulates

| Step | Action | Expected |
|------|--------|----------|
| 1 | Note current number of reports in history | Count recorded |
| 2 | Generate a new Rewind report | Report generated |
| 3 | Check history section | Count increased by 1 |
| 4 | New report appears in history list | Most recent at top |

### TC-RWGEN-06: Generate Rewind with no recent likes

| Step | Action | Expected |
|------|--------|----------|
| 1 | Unlike all articles (or test with fresh user) | No recent likes |
| 2 | Click "Generate Rewind" | Loading state |
| 3 | Report generates | Empty or "no activity" report |
| 4 | Hot Topics section | Empty or minimal |

### TC-RWGEN-07: Historical report detail view

| Step | Action | Expected |
|------|--------|----------|
| 1 | In Rewind history, click an older report | Report details expand |
| 2 | Verify different data from latest | Different hot topics / trends |
| 3 | Period dates match that week | Correct date range |

---

# Part B: Frontend UI

---

---

## 8. TC-NAV: Navigation

### TC-NAV-01: All pages load without errors

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `/` | Today page renders with article cards |
| 2 | Navigate to `/archive` | Archive page renders with calendar |
| 3 | Navigate to `/bookmarks` | Bookmarks page renders with saved articles |
| 4 | Navigate to `/rewind` | Rewind page renders with report |
| 5 | Navigate to `/settings` | Settings page renders with feeds list |
| 6 | Check console for errors at each page | No errors or warnings |

### TC-NAV-02: NavBar active link highlighting

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, inspect nav links | "Today" link has active style (bold/colored) |
| 2 | Click "Archive" | "Archive" link becomes active, "Today" is no longer active |
| 3 | Repeat for all 5 nav items | Only current page link is active at a time |

### TC-NAV-03: Browser back/forward navigation

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate: Today -> Archive -> Bookmarks | Pages load in sequence |
| 2 | Press browser Back | Returns to Archive, page renders correctly |
| 3 | Press browser Back again | Returns to Today, page renders correctly |
| 4 | Press browser Forward | Returns to Archive, page renders correctly |

### TC-NAV-04: Direct URL access

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate directly to `http://localhost:5173/archive` | Archive page loads (not 404) |
| 2 | Navigate directly to `http://localhost:5173/bookmarks` | Bookmarks page loads |
| 3 | Navigate to `http://localhost:5173/nonexistent` | Graceful handling (redirect to Today or 404 page) |

---

## 9. TC-TODAY: Today Page

### TC-TODAY-01: Article rendering and layout

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `/` | Page loads with newsletter date header |
| 2 | Verify category sections exist | 4 categories visible: AI/ML, Backend, DevOps, Frontend |
| 3 | Count total article cards | 10 articles displayed |
| 4 | Inspect a single article card | Shows: title, source, relevance score badge, summary text |
| 5 | Verify summary is in Korean | Summary text contains Korean characters |
| 6 | Verify relevance score format | Score displayed as 0.0-1.0 with colored badge |

### TC-TODAY-02: Article link behavior

| Step | Action | Expected |
|------|--------|----------|
| 1 | Take snapshot, find article title link | Title is a clickable link |
| 2 | Verify link `href` | Points to an external URL (not internal route) |
| 3 | Verify link has `target="_blank"` | Opens in new tab |
| 4 | Verify link has `rel="noopener noreferrer"` | Security attributes present |

### TC-TODAY-03: Like toggle interaction

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find a non-liked article's like button | Button appears in default/inactive state |
| 2 | Click the like button | Button changes to active state (filled/colored) |
| 3 | Click the same button again | Button returns to inactive state |
| 4 | Rapid double-click the like button | No visual glitch; final state is consistent |

### TC-TODAY-04: Bookmark toggle interaction

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find a non-bookmarked article's bookmark button | Button appears in default state |
| 2 | Click the bookmark button | Button changes to active state |
| 3 | Click the same button again | Button returns to inactive state |

### TC-TODAY-05: Pre-existing interaction states

| Step | Action | Expected |
|------|--------|----------|
| 1 | Take snapshot of Today page | Some articles show pre-liked or pre-bookmarked states (from mock data) |
| 2 | Identify pre-liked article | Like button is already in active/filled state |
| 3 | Identify pre-bookmarked article | Bookmark button is already in active/filled state |

### TC-TODAY-06: Loading state

| Step | Action | Expected |
|------|--------|----------|
| 1 | Hard reload the page | Brief skeleton/loading UI appears before content |
| 2 | Content loads | Skeleton is replaced by article cards smoothly |

### TC-TODAY-07: Category section collapse/expand (if implemented)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Take snapshot to check if category headers are clickable | Document whether collapse/expand exists |
| 2 | If clickable, click a category header | Section collapses, articles hidden |
| 3 | Click again | Section expands, articles visible again |

---

## 10. TC-ARCHIVE: Archive Page

### TC-ARCHIVE-01: Calendar view default state

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `/archive` | Calendar view for current month (February 2026) |
| 2 | Verify month/year header | Shows "February 2026" or similar |
| 3 | Verify day-of-week headers | Sun-Sat or Mon-Sun displayed |
| 4 | Check dates with editions | Dates with newsletters show badge/indicator (article count) |
| 5 | Check dates without editions | No badge, may be visually dimmed |

### TC-ARCHIVE-02: Date selection and article loading

| Step | Action | Expected |
|------|--------|----------|
| 1 | Before selecting a date | Prompt text shown (e.g., "Select a date to view articles") |
| 2 | Click a date with an edition badge | Articles for that date load below the calendar |
| 3 | Verify articles render like Today page | Category sections, cards with title/source/score/summary |
| 4 | Click a different date with edition | Previous articles replaced with new date's articles |
| 5 | Click a date without an edition | No articles shown; appropriate empty message |

### TC-ARCHIVE-03: Month navigation

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click "Previous month" button | Calendar shows January 2026 |
| 2 | Check for edition badges | No editions expected in January (mock data is Feb only) |
| 3 | Click "Next month" to return | Calendar shows February 2026 again |
| 4 | Verify edition badges restored | Same badges as initial load |

### TC-ARCHIVE-04: List view

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find and click view toggle (list icon) | Calendar switches to list view |
| 2 | Verify list shows editions | Chronologically sorted list of edition dates |
| 3 | Each edition shows article count | Badge or count label visible |
| 4 | Click an edition in list | Articles for that edition load |
| 5 | Toggle back to calendar view | Calendar view restored |

### TC-ARCHIVE-05: View switch preserves selection

| Step | Action | Expected |
|------|--------|----------|
| 1 | In calendar view, select a date | Articles load for that date |
| 2 | Switch to list view | Same edition is highlighted/selected in list |
| 3 | Switch back to calendar view | Same date remains selected, articles still shown |

### TC-ARCHIVE-06: Article interactions in archive

| Step | Action | Expected |
|------|--------|----------|
| 1 | Select a date with articles | Articles render with like/bookmark buttons |
| 2 | Like an article | Like button toggles to active |
| 3 | Bookmark an article | Bookmark button toggles to active |
| 4 | Select a different date, then return | Interaction states should be preserved |

---

## 11. TC-BOOKMARKS: Bookmarks Page

### TC-BOOKMARKS-01: Bookmarked articles display

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `/bookmarks` | Page loads with bookmarked article count |
| 2 | Verify article count matches header | Count label matches number of cards shown |
| 3 | Each article shows title, source, date | Basic info visible |
| 4 | Each article shows detailed summary | Background, Key Takeaways, Keywords sections |

### TC-BOOKMARKS-02: Detailed summary structure

| Step | Action | Expected |
|------|--------|----------|
| 1 | Inspect a bookmarked article's detailed summary | Has distinct sections |
| 2 | "Background" section | Contextual paragraph in Korean |
| 3 | "Key Takeaways" section | 3-5 bullet points |
| 4 | "Keywords" section | Keyword tags/badges displayed |

### TC-BOOKMARKS-03: Remove bookmark

| Step | Action | Expected |
|------|--------|----------|
| 1 | Note the current bookmark count | e.g., "2 articles" |
| 2 | Click "Remove" button on first article | Article disappears from list |
| 3 | Verify count updated | Now shows "1 article" |
| 4 | Remove the last bookmark | Empty state message appears |
| 5 | Verify empty state UI | Appropriate message (e.g., "No bookmarks yet") |

### TC-BOOKMARKS-04: External link from bookmarks

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find article title link | Clickable link present |
| 2 | Verify `href` and `target` | External URL with `target="_blank"` |

---

## 12. TC-REWIND: Rewind Page

### TC-REWIND-01: Latest report display

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `/rewind` | Latest weekly report loads |
| 2 | Verify report period | Shows date range (e.g., "Feb 9 - Feb 16, 2026") |
| 3 | Verify generation date | Creation timestamp displayed |
| 4 | Verify overview text | Summary paragraph present |

### TC-REWIND-02: Hot Topics section

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find "Hot Topics" section | Section header visible |
| 2 | Verify topic items | Topics with counts (e.g., "LLM Agents (5)") |
| 3 | Verify ordering | Topics sorted by count descending |

### TC-REWIND-03: Trend Changes section

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find rising trends | Items with positive values (e.g., "+2.7") |
| 2 | Verify rising trend styling | Green color or upward indicator |
| 3 | Find declining trends | Items with negative values (e.g., "-1.2") |
| 4 | Verify declining trend styling | Red color or downward indicator |

### TC-REWIND-04: Trend chart visualization

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find trend chart area | Bar chart or similar visualization rendered |
| 2 | Verify bar colors | Rising = green, Declining = red |
| 3 | Verify bar proportions | Larger values have wider/taller bars |

### TC-REWIND-05: Suggestions section

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find "Suggestions" section | Section visible |
| 2 | Verify suggestion items | 2-4 topic suggestions listed |

### TC-REWIND-06: Generate Rewind button

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find "Generate Rewind" button | Button visible and enabled |
| 2 | Click the button | Button shows loading state (spinner or "Generating...") |
| 3 | Wait for completion | Loading state resolves; new report appears or current report refreshes |

### TC-REWIND-07: Rewind history

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find history section | Past reports listed (4 items in mock data) |
| 2 | Each history item shows period | Date range visible |
| 3 | Click a history item | Report details expand or switch to that report |
| 4 | Verify report content changes | Different data from the latest report |
| 5 | Click back to latest or another history item | Report switches again |

---

## 13. TC-SETTINGS: Settings Page

### TC-SETTINGS-01: Feeds list display

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to `/settings` | Settings page with feeds section |
| 2 | Verify 5 feeds listed | TechCrunch, Hacker News, Medium, Dev.to, Python Weekly |
| 3 | Active feeds have enabled indicator | Green dot or active icon |
| 4 | Python Weekly shows inactive | Gray/disabled indicator |

### TC-SETTINGS-02: Feed active/inactive toggle

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click toggle on an active feed | Feed changes to inactive state |
| 2 | Visual indicator changes | Green -> gray or similar |
| 3 | Click toggle again | Feed returns to active state |

### TC-SETTINGS-03: Add new feed — happy path

| Step | Action | Expected |
|------|--------|----------|
| 1 | Find "Add feed" form | Name and URL input fields visible |
| 2 | Enter name: "Test Blog" | Name field populated |
| 3 | Enter URL: "https://testblog.com/rss" | URL field populated |
| 4 | Click "Add" button | New feed appears in the list |
| 5 | Verify new feed shows active state | Enabled by default |
| 6 | Verify feed count increased | 6 feeds now listed |

### TC-SETTINGS-04: Add feed — URL validation

| Step | Action | Expected |
|------|--------|----------|
| 1 | Enter name: "Bad Feed" | Name field populated |
| 2 | Enter URL: "not-a-url" | URL field populated |
| 3 | Click "Add" | Error message appears (invalid URL) |
| 4 | Feed is NOT added to list | List still shows original feeds |
| 5 | Enter URL: "ftp://example.com" | Invalid protocol |
| 6 | Click "Add" | Error message (must be http/https) |
| 7 | Clear and enter URL: "https://valid.com/feed" | Valid URL |
| 8 | Click "Add" | Feed added successfully |

### TC-SETTINGS-05: Add feed — empty fields

| Step | Action | Expected |
|------|--------|----------|
| 1 | Leave both fields empty, click "Add" | Validation error or button disabled |
| 2 | Enter name only, click "Add" | URL required error |
| 3 | Enter URL only, click "Add" | Name required error |

### TC-SETTINGS-06: Delete feed — confirmation flow

| Step | Action | Expected |
|------|--------|----------|
| 1 | Click delete button on a feed | Confirmation prompt appears (not immediately deleted) |
| 2 | Cancel the confirmation | Feed remains in list |
| 3 | Click delete again | Confirmation prompt appears |
| 4 | Confirm deletion | Feed removed from list |
| 5 | Verify feed count decreased | One fewer feed |

### TC-SETTINGS-07: Interests profile display

| Step | Action | Expected |
|------|--------|----------|
| 1 | Scroll to interests section | Section header visible |
| 2 | Verify 8 keywords listed | machine-learning, kubernetes, python, etc. |
| 3 | Each keyword shows weight | Numeric value (e.g., "5.2") |
| 4 | Bar chart visualization | Bar width proportional to weight |
| 5 | Highest weight has widest bar | machine-learning (5.2) should be widest |
| 6 | Tip text present | "Liking related articles increases weight" or similar |

### TC-SETTINGS-08: Interests weight bar proportions

| Step | Action | Expected |
|------|--------|----------|
| 1 | Take screenshot of interest bars | Bars visible |
| 2 | Compare top weight (5.2) vs lowest (1.0) | ~5:1 width ratio visually |
| 3 | Middle weights have proportional widths | Smooth gradient from widest to narrowest |

---

## 14. TC-CROSS: Cross-Page Interactions

### TC-CROSS-01: Bookmark on Today -> appears on Bookmarks page

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Today page | Articles loaded |
| 2 | Find a non-bookmarked article, note its title | Title recorded |
| 3 | Click bookmark button | Button becomes active |
| 4 | Navigate to Bookmarks page | Page loads |
| 5 | Verify the bookmarked article appears | Article title found in bookmarks list |

### TC-CROSS-02: Remove bookmark on Bookmarks -> reflected on Today

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Bookmarks page, remove a bookmark | Article removed from list |
| 2 | Navigate to Today page | Page loads |
| 3 | Find the same article | Bookmark button is now in inactive state |

### TC-CROSS-03: Like on Today -> persists across navigation

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, like an article | Like button active |
| 2 | Navigate to Archive page | Archive loads |
| 3 | Navigate back to Today | Today loads |
| 4 | Verify the liked article | Like button still in active state |

### TC-CROSS-04: Interactions in Archive -> visible on Today

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Archive | Calendar loads |
| 2 | Select today's date | Today's articles load |
| 3 | Like an article in Archive view | Like button active |
| 4 | Navigate to Today page | Same article shows liked state |

---

## 15. TC-RESPONSIVE: Responsive Design

### TC-RESPONSIVE-01: Mobile layout (375px)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Resize browser to 375x812 (iPhone SE) | Layout adapts |
| 2 | Verify NavBar | Hamburger menu or adapted navigation |
| 3 | Verify Today page | Article cards stack vertically, no horizontal overflow |
| 4 | Verify text readability | Font size adequate, no truncated text |
| 5 | Verify buttons are tappable | Minimum 44x44px touch targets |
| 6 | Take screenshot | Document mobile layout |

### TC-RESPONSIVE-02: Tablet layout (768px)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Resize browser to 768x1024 (iPad) | Layout adapts |
| 2 | Verify NavBar | Visible and properly spaced |
| 3 | Verify article cards | May show 2-column grid or single column |
| 4 | Verify Archive calendar | Calendar fits without overflow |
| 5 | Take screenshot | Document tablet layout |

### TC-RESPONSIVE-03: Desktop layout (1280px)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Resize browser to 1280x800 | Standard desktop layout |
| 2 | Verify content width | Max-width container, not full bleed |
| 3 | Verify all pages render properly | No layout issues |
| 4 | Take screenshot | Document desktop layout |

### TC-RESPONSIVE-04: Wide screen (1920px)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Resize browser to 1920x1080 | Wide desktop layout |
| 2 | Content should be centered or max-width | Not stretched to full width |
| 3 | No awkward whitespace | Layout still looks intentional |

### TC-RESPONSIVE-05: Archive calendar on mobile

| Step | Action | Expected |
|------|--------|----------|
| 1 | Resize to 375px, navigate to Archive | Calendar view loads |
| 2 | Verify calendar fits screen | No horizontal scroll needed |
| 3 | Date cells are tappable | Minimum touch target size |
| 4 | Month navigation buttons accessible | Buttons visible and tappable |

### TC-RESPONSIVE-06: Settings page on mobile

| Step | Action | Expected |
|------|--------|----------|
| 1 | Resize to 375px, navigate to Settings | Page loads |
| 2 | Feed list readable | Feed names and controls visible |
| 3 | Add feed form usable | Input fields and button accessible |
| 4 | Interest bars visible | Bar chart readable on small screen |

---

## 16. TC-A11Y: Accessibility

### TC-A11Y-01: Keyboard navigation — full flow

| Step | Action | Expected |
|------|--------|----------|
| 1 | Press Tab from page load | Focus moves to first interactive element |
| 2 | Continue Tab through NavBar | Each nav link receives focus with visible indicator |
| 3 | Press Enter on a nav link | Navigates to that page |
| 4 | Tab through article cards | Focus reaches like/bookmark buttons |
| 5 | Press Enter/Space on like button | Like toggles |
| 6 | Press Enter/Space on bookmark button | Bookmark toggles |
| 7 | Shift+Tab | Focus moves backwards correctly |

### TC-A11Y-02: Focus visibility

| Step | Action | Expected |
|------|--------|----------|
| 1 | Tab through elements | Each focused element has visible focus ring/outline |
| 2 | Focus ring contrast | Ring is clearly distinguishable from background |
| 3 | Focus ring on buttons | Like/bookmark/toggle buttons show clear focus |
| 4 | Focus ring on links | Article title links show clear focus |
| 5 | Focus ring on form inputs | Settings page inputs show focus |

### TC-A11Y-03: ARIA labels and roles

| Step | Action | Expected |
|------|--------|----------|
| 1 | Take snapshot of Today page | Check for aria-labels in snapshot |
| 2 | Like buttons | Have descriptive aria-label (e.g., "Like article: [title]") |
| 3 | Bookmark buttons | Have descriptive aria-label |
| 4 | Navigation links | Properly labeled |
| 5 | Settings toggles | Have aria-label indicating feed name and state |

### TC-A11Y-04: Semantic HTML structure

| Step | Action | Expected |
|------|--------|----------|
| 1 | Check page structure via snapshot | Proper heading hierarchy (h1 > h2 > h3) |
| 2 | Navigation uses `<nav>` element | Semantic navigation landmark |
| 3 | Main content in `<main>` | Semantic main landmark |
| 4 | Article cards use `<article>` or proper sectioning | Semantic markup |
| 5 | Lists use `<ul>`/`<ol>` elements | Proper list semantics |

### TC-A11Y-05: Settings form accessibility

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Settings with keyboard | Page loads |
| 2 | Tab to feed name input | Input receives focus with label |
| 3 | Tab to URL input | Input receives focus with label |
| 4 | Tab to Add button | Button receives focus |
| 5 | Press Enter | Form submits (if valid) |
| 6 | Error state | Error message associated with input (aria-describedby) |

---

## 17. TC-VISUAL: Visual & UX Polish

### TC-VISUAL-01: Color consistency

| Step | Action | Expected |
|------|--------|----------|
| 1 | Take screenshots of all 5 pages | Full page captures |
| 2 | Verify primary color usage | Consistent brand color across pages |
| 3 | Verify like button colors | Inactive = gray, Active = indigo/purple |
| 4 | Verify bookmark button colors | Inactive = gray, Active = amber/yellow |
| 5 | Verify score badge colors | Consistent color scale (low=red, mid=yellow, high=green or similar) |

### TC-VISUAL-02: Typography consistency

| Step | Action | Expected |
|------|--------|----------|
| 1 | Compare page titles across pages | Same font size and weight |
| 2 | Compare section headers | Consistent heading style |
| 3 | Compare body text | Same font family and size |
| 4 | Korean text rendering | No font fallback issues, proper Korean font |

### TC-VISUAL-03: Spacing and alignment

| Step | Action | Expected |
|------|--------|----------|
| 1 | Verify card spacing | Consistent gaps between article cards |
| 2 | Verify section spacing | Consistent gaps between category sections |
| 3 | Verify button alignment | Like/bookmark buttons aligned within cards |
| 4 | Verify text alignment | Left-aligned text, no jagged edges |

### TC-VISUAL-04: Loading skeleton quality

| Step | Action | Expected |
|------|--------|----------|
| 1 | Hard reload Today page | Skeleton appears briefly |
| 2 | Skeleton matches content layout | Skeleton shapes approximate article cards |
| 3 | Skeleton has pulse animation | Smooth animated shimmer effect |
| 4 | Transition to content | Clean swap, no layout shift |

### TC-VISUAL-05: Empty states

| Step | Action | Expected |
|------|--------|----------|
| 1 | Remove all bookmarks on Bookmarks page | Empty state appears |
| 2 | Verify empty state UI | Friendly message, possibly an illustration or icon |
| 3 | Empty state is centered | Not stuck in top-left corner |
| 4 | Message is helpful | Suggests how to add bookmarks |

### TC-VISUAL-06: Button hover and active states

| Step | Action | Expected |
|------|--------|----------|
| 1 | Hover over like button | Visual feedback (color change, scale, or opacity) |
| 2 | Hover over bookmark button | Similar visual feedback |
| 3 | Hover over nav links | Underline, color change, or other indicator |
| 4 | Hover over "Add" button in Settings | Button highlight |
| 5 | Click and hold a button | Active/pressed state visible |

### TC-VISUAL-07: Scroll behavior

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, scroll down | NavBar stays fixed (sticky) or scrolls away |
| 2 | Scroll smoothly | No jank or stuttering |
| 3 | On long article list, scroll to bottom | All articles render (no infinite scroll cutoff) |
| 4 | Scroll back to top | Smooth scroll, content intact |

---

---

# Part C: Full Integration

---

## 18. TC-E2E: End-to-End Integration

> Full user journey tests that span pipeline execution, UI interaction, and data persistence.
> These are the highest-value tests — they validate the entire system working together.

### TC-E2E-01: First-time user journey — Pipeline to UI

| Step | Action | Expected |
|------|--------|----------|
| 1 | Verify backend running: `GET /api/health` | `{"status": "ok"}` |
| 2 | Navigate to `http://localhost:5173` (Today page) | Page loads (may show empty state if no pipeline run yet) |
| 3 | Trigger pipeline via browser console: `fetch('/api/pipeline/run', {method: 'POST'})` | Pipeline executes |
| 4 | Reload Today page | Articles from real RSS feeds appear |
| 5 | Verify articles have Korean summaries | Summary text in Korean |
| 6 | Verify articles have relevance scores | Scores 0.3-1.0 as badges |
| 7 | Verify articles grouped by categories | Category section headers visible |
| 8 | Click an article title | Opens original article URL in new tab |

### TC-E2E-02: Like → Interest update → Improved scoring cycle

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Settings, record interest weights | Baseline weights noted |
| 2 | Navigate to Today page | Articles displayed |
| 3 | Like 3-5 articles about a specific topic (e.g., AI/ML) | Like buttons active |
| 4 | Navigate to Settings → interests | Weights for liked topic keywords increased |
| 5 | Trigger pipeline: `POST /api/pipeline/run` | New articles scored |
| 6 | Reload Today page | New articles appear |
| 7 | Compare: AI/ML article scores should be higher than before | Interest-based scoring improvement visible |

### TC-E2E-03: Bookmark → Detailed summary → Bookmarks page

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, bookmark an article | Bookmark button active |
| 2 | Wait 5-10 seconds for async Gemini call | Background task completes |
| 3 | Navigate to Bookmarks page | Bookmarked article appears |
| 4 | Verify detailed summary with Background / Key Takeaways / Keywords | All sections populated with Korean content |
| 5 | Verify keywords match article topic | Relevant technical keywords |
| 6 | Click article title link | Opens original article URL |

### TC-E2E-04: Full Rewind cycle — Likes over time → Report

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ensure ≥ 5 articles are liked across different categories | Likes registered |
| 2 | Navigate to Rewind page | Page loads |
| 3 | Click "Generate Rewind" | Loading state, then report appears |
| 4 | Verify Hot Topics reflect liked article categories | Topics match likes |
| 5 | Verify Trend Changes section | Rising/declining trends present |
| 6 | Verify Suggestions section | Actionable keyword suggestions |
| 7 | Check Rewind history | New report appears in history |

### TC-E2E-05: Feed management → Pipeline → Article sourcing

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to Settings | Feed list displayed |
| 2 | Disable one feed (e.g., TechCrunch) | Feed toggled to inactive |
| 3 | Run pipeline: `POST /api/pipeline/run` | Pipeline completes |
| 4 | Navigate to Today page | No articles from disabled feed |
| 5 | Re-enable the feed | Feed toggled to active |
| 6 | Add a new feed with valid RSS URL | Feed added to list |
| 7 | Run pipeline again | Articles from new feed appear |

### TC-E2E-06: Archive browsing with real data

| Step | Action | Expected |
|------|--------|----------|
| 1 | After at least one pipeline run, navigate to Archive | Calendar view |
| 2 | Today's date should have an edition badge | Article count indicator visible |
| 3 | Click today's date | Real articles load (same as Today page) |
| 4 | Like/bookmark an article in Archive | Interaction persists |
| 5 | Navigate to Today page | Same interaction state visible |
| 6 | Navigate to Bookmarks page | Bookmarked article appears with details |

### TC-E2E-07: Cross-page interaction consistency with real data

| Step | Action | Expected |
|------|--------|----------|
| 1 | On Today page, like Article A and bookmark Article B | Both interactions registered |
| 2 | Navigate to Archive, select today | Article A shows liked, Article B shows bookmarked |
| 3 | Navigate to Bookmarks | Article B appears with detailed summary |
| 4 | Remove bookmark from Article B on Bookmarks page | Article B removed |
| 5 | Navigate back to Today | Article B's bookmark button is inactive |
| 6 | Navigate to Archive, select today | Article B's bookmark button is inactive |

### TC-E2E-08: Pipeline error recovery

| Step | Action | Expected |
|------|--------|----------|
| 1 | Run pipeline successfully once | Articles appear on Today page |
| 2 | Run pipeline again immediately | Pipeline handles deduplication gracefully |
| 3 | Result shows fewer new articles | Dedup working — not duplicating existing articles |
| 4 | Existing articles on Today page unchanged | No data corruption |
| 5 | Previously liked/bookmarked articles retain their state | Interactions preserved |

---

## Test Execution Checklist

| ID | Scenario | Priority | Status |
|----|----------|----------|--------|
| **Part A: Backend Pipeline** | | | |
| TC-PIPE-01 | Trigger pipeline and verify result | Critical | |
| TC-PIPE-02 | Pipeline idempotency (dedup) | Critical | |
| TC-PIPE-03 | Pipeline result via newsletter API | Critical | |
| TC-PIPE-04 | Pipeline resilience (partial failure) | High | |
| TC-FEED-01 | Active feeds collected | Critical | |
| TC-FEED-02 | Inactive feeds skipped | High | |
| TC-FEED-03 | New feed added and collected | High | |
| TC-FEED-04 | Feed deletion stops collection | High | |
| TC-FEED-05 | Article deduplication | Critical | |
| TC-SCORE-01 | Valid relevance scores | Critical | |
| TC-SCORE-02 | Categories and keywords | High | |
| TC-SCORE-03 | Scoring reflects interests | High | |
| TC-SCORE-04 | Max 20 articles per newsletter | High | |
| TC-SUMMARY-01 | Basic summaries in Korean | Critical | |
| TC-SUMMARY-02 | Detailed summary on bookmark | Critical | |
| TC-SUMMARY-03 | Detailed summary persistence | Medium | |
| TC-FEEDBACK-01 | Like increases interest weights | Critical | |
| TC-FEEDBACK-02 | Unlike decreases interest weights | Critical | |
| TC-FEEDBACK-03 | New interest keyword on like | High | |
| TC-FEEDBACK-04 | Interest influences next scoring | High | |
| TC-FEEDBACK-05 | Interest bar chart updates | Medium | |
| TC-RWGEN-01 | Generate Rewind with likes | Critical | |
| TC-RWGEN-02 | Hot Topics reflect likes | High | |
| TC-RWGEN-03 | Trend Changes section | High | |
| TC-RWGEN-04 | Suggestions are actionable | Medium | |
| TC-RWGEN-05 | Rewind history accumulates | High | |
| TC-RWGEN-06 | Generate with no recent likes | Medium | |
| TC-RWGEN-07 | Historical report detail view | Medium | |
| **Part B: Frontend UI** | | | |
| TC-NAV-01 | All pages load | Critical | |
| TC-NAV-02 | NavBar active link | High | |
| TC-NAV-03 | Back/forward navigation | Medium | |
| TC-NAV-04 | Direct URL access | Medium | |
| TC-TODAY-01 | Article rendering | Critical | |
| TC-TODAY-02 | Article link behavior | High | |
| TC-TODAY-03 | Like toggle | Critical | |
| TC-TODAY-04 | Bookmark toggle | Critical | |
| TC-TODAY-05 | Pre-existing states | High | |
| TC-TODAY-06 | Loading state | Medium | |
| TC-TODAY-07 | Category collapse | Low | |
| TC-ARCHIVE-01 | Calendar default | High | |
| TC-ARCHIVE-02 | Date selection | Critical | |
| TC-ARCHIVE-03 | Month navigation | High | |
| TC-ARCHIVE-04 | List view | High | |
| TC-ARCHIVE-05 | View switch preserve | Medium | |
| TC-ARCHIVE-06 | Archive interactions | High | |
| TC-BOOKMARKS-01 | Bookmarks display | Critical | |
| TC-BOOKMARKS-02 | Detailed summary | High | |
| TC-BOOKMARKS-03 | Remove bookmark | Critical | |
| TC-BOOKMARKS-04 | External link | Medium | |
| TC-REWIND-01 | Latest report | Critical | |
| TC-REWIND-02 | Hot Topics | High | |
| TC-REWIND-03 | Trend Changes | High | |
| TC-REWIND-04 | Trend chart | High | |
| TC-REWIND-05 | Suggestions | Medium | |
| TC-REWIND-06 | Generate button | High | |
| TC-REWIND-07 | Rewind history | High | |
| TC-SETTINGS-01 | Feeds list | Critical | |
| TC-SETTINGS-02 | Feed toggle | High | |
| TC-SETTINGS-03 | Add feed | Critical | |
| TC-SETTINGS-04 | URL validation | High | |
| TC-SETTINGS-05 | Empty field validation | Medium | |
| TC-SETTINGS-06 | Delete feed | High | |
| TC-SETTINGS-07 | Interests display | High | |
| TC-SETTINGS-08 | Weight bar proportions | Medium | |
| TC-CROSS-01 | Bookmark Today->Bookmarks | Critical | |
| TC-CROSS-02 | Remove bookmark->Today | Critical | |
| TC-CROSS-03 | Like persists navigation | High | |
| TC-CROSS-04 | Archive<->Today sync | High | |
| TC-RESPONSIVE-01 | Mobile 375px | High | |
| TC-RESPONSIVE-02 | Tablet 768px | Medium | |
| TC-RESPONSIVE-03 | Desktop 1280px | Medium | |
| TC-RESPONSIVE-04 | Wide 1920px | Low | |
| TC-RESPONSIVE-05 | Calendar mobile | High | |
| TC-RESPONSIVE-06 | Settings mobile | Medium | |
| TC-A11Y-01 | Keyboard navigation | High | |
| TC-A11Y-02 | Focus visibility | High | |
| TC-A11Y-03 | ARIA labels | Medium | |
| TC-A11Y-04 | Semantic HTML | Medium | |
| TC-A11Y-05 | Settings form a11y | Medium | |
| TC-VISUAL-01 | Color consistency | Medium | |
| TC-VISUAL-02 | Typography | Medium | |
| TC-VISUAL-03 | Spacing alignment | Medium | |
| TC-VISUAL-04 | Loading skeleton | Medium | |
| TC-VISUAL-05 | Empty states | Medium | |
| TC-VISUAL-06 | Hover/active states | Low | |
| TC-VISUAL-07 | Scroll behavior | Medium | |
| **Part C: Full Integration** | | | |
| TC-E2E-01 | Pipeline to UI first journey | Critical | |
| TC-E2E-02 | Like → Interest → Scoring cycle | Critical | |
| TC-E2E-03 | Bookmark → Detailed summary | Critical | |
| TC-E2E-04 | Full Rewind cycle | Critical | |
| TC-E2E-05 | Feed management → Pipeline | High | |
| TC-E2E-06 | Archive with real data | High | |
| TC-E2E-07 | Cross-page consistency (real data) | High | |
| TC-E2E-08 | Pipeline error recovery | High | |
