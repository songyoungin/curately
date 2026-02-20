# Bookmarks Sort by Most Recently Bookmarked Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Sort the bookmarked articles list by most recently bookmarked (newest first), instead of the current undefined order.

**Architecture:** The `interactions` table already stores `created_at` per bookmark. We fetch bookmark interactions ordered by `created_at DESC`, then reorder the articles to match that order after the `.in_()` query (which does not preserve input order).

**Tech Stack:** FastAPI, Supabase (PostgreSQL), pytest, MSW (Playwright e2e)

---

### Task 1: Backend — Write failing test for bookmark ordering

**Files:**
- Modify: `tests/test_articles.py`

**Step 1: Write the failing test**

Add a new test that verifies bookmarked articles are returned in reverse-chronological bookmark order. The mock returns two bookmark interactions with different `created_at` timestamps and two articles with IDs in ascending order. The test asserts the response returns articles ordered by bookmark `created_at` DESC (article 2 first, then article 1).

```python
@patch("backend.routers.articles.get_supabase_client")
def test_list_bookmarked_articles_ordered_by_recent(mock_get_client: MagicMock) -> None:
    """Verify bookmarked articles are sorted by bookmark time, newest first.

    Mock: two bookmark interactions with different created_at timestamps,
    two matching articles returned in id-ascending order by Supabase.
    Expects: articles reordered so that the more recently bookmarked article comes first.
    """
    mock_client = MagicMock()

    # interactions table: select("article_id, created_at").eq(user_id).eq(type).order(created_at desc)
    mock_interactions = MagicMock()
    mock_interactions.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {"article_id": 2, "created_at": "2026-02-20T12:00:00+00:00"},
            {"article_id": 1, "created_at": "2026-02-19T08:00:00+00:00"},
        ]
    )

    # articles table: select(columns).in_(id, [...]).execute() — returns in id order
    mock_articles = MagicMock()
    mock_articles.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": 1,
                "source_feed": "Feed A",
                "source_url": "https://example.com/1",
                "title": "Older Bookmark",
                "author": "Author A",
                "published_at": "2026-02-18T10:00:00+00:00",
                "summary": "Summary 1",
                "detailed_summary": None,
                "relevance_score": 0.8,
                "categories": ["tech"],
                "keywords": ["python"],
                "newsletter_date": "2026-02-18",
            },
            {
                "id": 2,
                "source_feed": "Feed B",
                "source_url": "https://example.com/2",
                "title": "Newer Bookmark",
                "author": "Author B",
                "published_at": "2026-02-19T10:00:00+00:00",
                "summary": "Summary 2",
                "detailed_summary": None,
                "relevance_score": 0.7,
                "categories": ["devops"],
                "keywords": ["k8s"],
                "newsletter_date": "2026-02-19",
            },
        ]
    )

    # _attach_interaction_flags needs interactions table for flag lookup
    mock_flag_interactions = MagicMock()
    mock_flag_interactions.select.return_value.eq.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {"article_id": 1, "type": "bookmark"},
            {"article_id": 2, "type": "bookmark"},
        ]
    )

    call_count = {"interactions": 0}

    def route_table(name: str) -> MagicMock:
        if name == "interactions":
            call_count["interactions"] += 1
            # First call: fetch bookmark article_ids (ordered)
            # Second call: _attach_interaction_flags
            if call_count["interactions"] == 1:
                return mock_interactions
            return mock_flag_interactions
        if name == "articles":
            return mock_articles
        return MagicMock()

    mock_client.table.side_effect = route_table
    mock_get_client.return_value = mock_client

    response = client.get("/api/articles/bookmarked")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Most recently bookmarked article should come first
    assert data[0]["id"] == 2
    assert data[0]["title"] == "Newer Bookmark"
    assert data[1]["id"] == 1
    assert data[1]["title"] == "Older Bookmark"
```

**Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_articles.py::test_list_bookmarked_articles_ordered_by_recent -v`
Expected: FAIL — the current endpoint does not apply ordering.

**Step 3: Commit the failing test**

```bash
git add tests/test_articles.py
git commit -m "test: add failing test for bookmark ordering by most recent"
```

---

### Task 2: Backend — Implement bookmark ordering in endpoint

**Files:**
- Modify: `backend/routers/articles.py:66-95` (the `list_bookmarked_articles` function)

**Step 1: Modify the endpoint to order by bookmark `created_at` DESC**

Replace the `list_bookmarked_articles` function with this implementation:

```python
@router.get("/bookmarked", response_model=list[ArticleListItem])
async def list_bookmarked_articles(
    user_id: int = Depends(get_current_user_id),
) -> list[dict[str, Any]]:
    """Return all bookmarked articles for the authenticated user.

    Articles are sorted by bookmark creation time, most recent first.
    """
    client = get_supabase_client()

    # Fetch bookmark interactions ordered by most recently bookmarked
    bookmark_result = (
        client.table("interactions")
        .select("article_id, created_at")
        .eq("user_id", user_id)
        .eq("type", "bookmark")
        .order("created_at", desc=True)
        .execute()
    )
    bookmark_rows = cast(list[dict[str, Any]], bookmark_result.data)

    if not bookmark_rows:
        return []

    article_ids = [row["article_id"] for row in bookmark_rows]
    articles_result = (
        client.table("articles")
        .select(_ARTICLE_LIST_COLUMNS)
        .in_("id", article_ids)
        .execute()
    )
    articles = cast(list[dict[str, Any]], articles_result.data)

    # Reorder articles to match bookmark creation order (most recent first)
    article_map = {a["id"]: a for a in articles}
    ordered_articles = [article_map[aid] for aid in article_ids if aid in article_map]

    return _attach_interaction_flags(ordered_articles, user_id)
```

Key changes:
1. `.select("article_id")` → `.select("article_id, created_at")` to fetch timestamp
2. Added `.order("created_at", desc=True)` to sort interactions by newest first
3. After fetching articles (which come back in arbitrary order from `.in_()`), reorder them using `article_map` to match the interaction order

**Step 2: Run the test to verify it passes**

Run: `uv run pytest tests/test_articles.py -v`
Expected: ALL PASS, including `test_list_bookmarked_articles_ordered_by_recent`

**Step 3: Run linter**

Run: `uv run pre-commit run --all-files`
Expected: PASS

**Step 4: Commit**

```bash
git add backend/routers/articles.py
git commit -m "feat: sort bookmarked articles by most recently bookmarked"
```

---

### Task 3: MSW mock handler — Sort bookmarked articles by ID descending

The MSW handler currently returns bookmarked articles filtered from `mockArticles` without sorting. Update it to simulate the new backend behavior. Since mock data doesn't have bookmark timestamps, use reverse array order as a reasonable approximation (higher-ID articles treated as more recently bookmarked).

**Files:**
- Modify: `frontend/src/mocks/handlers.ts:89-92`

**Step 1: Update the MSW bookmarked handler**

Replace:
```typescript
  http.get('/api/articles/bookmarked', () => {
    return HttpResponse.json(mockArticles.filter((a) => a.is_bookmarked));
  }),
```

With:
```typescript
  http.get('/api/articles/bookmarked', () => {
    const bookmarked = mockArticles.filter((a) => a.is_bookmarked);
    // Simulate backend ordering: most recently bookmarked first (higher ID = more recent)
    bookmarked.sort((a, b) => b.id - a.id);
    return HttpResponse.json(bookmarked);
  }),
```

**Step 2: Run e2e tests**

Run: `cd frontend && npx playwright test e2e/bookmarks.spec.ts`
Expected: ALL PASS (existing tests don't assert specific order between the two bookmarked articles)

**Step 3: Commit**

```bash
git add frontend/src/mocks/handlers.ts
git commit -m "fix: sort MSW bookmarked response by most recent first"
```

---

### Task 4: Add `data-testid` to BookmarkCard + E2E order test

`BookmarkCard` currently has no `data-testid`, making e2e selectors fragile. Add the testid first, then write a robust order verification test.

**Files:**
- Modify: `frontend/src/components/BookmarkCard.tsx:179`
- Modify: `frontend/e2e/bookmarks.spec.ts`

**Step 1: Add `data-testid` to BookmarkCard root element**

In `BookmarkCard.tsx`, replace the root `<div>`:

```tsx
    <div className="bg-white rounded-lg shadow-sm p-5 hover:shadow-md transition-shadow border border-gray-100">
```

With:

```tsx
    <div data-testid="bookmark-card" className="bg-white rounded-lg shadow-sm p-5 hover:shadow-md transition-shadow border border-gray-100">
```

**Step 2: Add order verification e2e test**

Append this test inside the existing `test.describe('Bookmarks Page', ...)` block in `bookmarks.spec.ts`:

```typescript
  test('should display bookmarks in most-recently-bookmarked order', async ({
    page,
  }) => {
    // With MSW mock sorting by descending ID, PostgreSQL (id=8) should appear before Kubernetes (id=5)
    const cards = page.locator('[data-testid="bookmark-card"]');
    await expect(cards).toHaveCount(2);

    const firstCardText = await cards.nth(0).textContent();
    const secondCardText = await cards.nth(1).textContent();
    expect(firstCardText).toContain('PostgreSQL');
    expect(secondCardText).toContain('Kubernetes');
  });
```

**Step 3: Run e2e tests**

Run: `cd frontend && npx playwright test e2e/bookmarks.spec.ts`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add frontend/src/components/BookmarkCard.tsx frontend/e2e/bookmarks.spec.ts
git commit -m "test: add data-testid to BookmarkCard and e2e order verification test"
```

---

### Task 5: Final Acceptance — Full CI validation + browser smoke test

Run the complete CI pipeline locally to verify nothing is broken, then perform a manual browser check with the real backend.

**Step 1: Run full backend test suite**

Run: `uv run pytest -v`
Expected: ALL PASS

**Step 2: Run linter + type check**

Run: `uv run pre-commit run --all-files`
Expected: ALL PASS

**Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: ALL PASS

**Step 4: Run full e2e test suite**

Run: `cd frontend && npx playwright test`
Expected: ALL PASS (all specs, not just bookmarks)

**Step 5: Browser smoke test with real backend**

Start backend and frontend connected to real API:

```bash
# Terminal 1: backend
uv run uvicorn backend.main:app --reload

# Terminal 2: frontend (MSW disabled)
cd frontend && VITE_ENABLE_MSW=false npm run dev
```

Manual verification:
1. Log in and navigate to Bookmarks page
2. Bookmark two articles from the Today page at different times (note the order)
3. Go to Bookmarks page — the more recently bookmarked article should appear first
4. Refresh the page — order should persist (server-side ordering, not client)

**Step 6: Final commit (if any fixes needed)**

If Steps 1–5 revealed issues, fix and commit. Otherwise, no action needed.

---

## Acceptance Criteria

| # | Criterion | Verified By |
|---|-----------|-------------|
| 1 | `GET /api/articles/bookmarked` returns articles ordered by bookmark `created_at` DESC | Backend unit test (`test_list_bookmarked_articles_ordered_by_recent`) |
| 2 | Bookmarks page renders articles in most-recently-bookmarked order | E2E test (`should display bookmarks in most-recently-bookmarked order`) |
| 3 | Order persists across page refresh (server-side, not client-side sort) | Manual browser smoke test (Task 5, Step 5) |
| 4 | No regressions in existing functionality | Full CI suite: `pytest` + `pre-commit` + `npm run lint` + `playwright test` |

---

## Summary of Changes

| Layer | File | Change |
|-------|------|--------|
| Backend endpoint | `backend/routers/articles.py` | Add `.order("created_at", desc=True)` + reorder articles by interaction order |
| Backend test | `tests/test_articles.py` | Add `test_list_bookmarked_articles_ordered_by_recent` |
| MSW mock | `frontend/src/mocks/handlers.ts` | Sort bookmarked filter result by descending ID |
| Frontend component | `frontend/src/components/BookmarkCard.tsx` | Add `data-testid="bookmark-card"` |
| E2E test | `frontend/e2e/bookmarks.spec.ts` | Add order verification test |
| Frontend UI logic | No changes | `useBookmarks` + `Bookmarks.tsx` render in response order (already correct) |
