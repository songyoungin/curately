# Multimodal Article Summaries

## 1. Background
Currently, Curately's pipeline extracts only the text from the `<summary>` or `<description>` tags provided by RSS feeds (`feedparser`) and passes it to the Gemini model. This approach causes the following issues:
- **Missing Information**: RSS summaries usually contain only shallow, headline-level information, making it difficult to grasp the full context of the article.
- **Lack of Visual Data**: For new LLM model announcements or research papers, key information is often embedded in images like benchmark tables or architecture diagrams. Currently, only text is passed, making it impossible to generate highly valuable summaries.

## 2. Goals
- **Scrape Full Content**: Extract the full article content from the original URL rather than relying on the RSS summary to secure rich context.
- **Extract Key Images**: Download core images (e.g., tables, diagrams) from the article to fully utilize Gemini 2.5 Flash's multimodal capabilities.
- **Improve Summary Quality**: Significantly enhance the depth and value of the summaries displayed on the Today, Bookmark, and Digest pages.

## 3. Acceptance Criteria (Definition of Done)
*The agent can use these criteria to self-evaluate if the task is complete.*
- [ ] All new services (`scraper.py`) and modified services (`summarizer.py`, `gemini.py`, `pipeline.py`) have passing unit tests written before the implementation (TDD).
- [ ] The system successfully extracts the full Markdown content and image URLs given a standard article URL.
- [ ] The system successfully downloads at least one valid image and passes its byte data along with the text to the Gemini API without raising errors.
- [ ] The generated summaries (both basic and detailed) demonstrably include information derived from the article's images (e.g., specific benchmark numbers from a table image).
- [ ] If scraping or image downloading fails (e.g., due to network errors or blocking), the system gracefully falls back to using the original RSS summary text without breaking the pipeline.

## 4. Simple Interfaces
*High-level interfaces to be implemented. Avoid deep implementation details here.*

**`backend/services/scraper.py` (New)**
```python
from typing import TypedDict

class ScrapedContent(TypedDict):
    markdown_text: str
    image_urls: list[str]

async def scrape_article(url: str) -> ScrapedContent:
    """Scrapes the URL and returns full markdown content and a list of image URLs."""
    ...

async def download_images(urls: list[str], max_images: int = 3) -> list[bytes]:
    """Downloads up to `max_images` from the provided URLs."""
    ...
```

**`backend/services/gemini.py` (Modified)**
```python
from google import genai
from typing import Any

async def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    contents: str | list[Any], # Modified to accept mixed content (text + image bytes)
    config: genai.types.GenerateContentConfig | None = None,
) -> str:
    ...
```

**`backend/services/summarizer.py` (Modified)**
```python
async def generate_basic_summary(
    title: str,
    content: str | None,
    images: list[bytes] | None = None # New parameter
) -> str:
    ...

async def generate_detailed_summary(
    title: str,
    content: str | None,
    images: list[bytes] | None = None # New parameter
) -> DetailedSummary:
    ...
```

## 5. TDD Approach & Checklist
*Strict Test-Driven Development workflow. Write tests first, make them pass, then refactor.*

### Phase 1: Scraper Service
- [ ] **Test**: Write tests for `backend/services/scraper.py` (mocking HTTP responses for full content extraction and image URL parsing).
- [ ] **Implement**: `backend/services/scraper.py` (`scrape_article`) to make tests pass (e.g., using Jina Reader API `https://r.jina.ai/` or similar).
- [ ] **Test**: Write tests for asynchronous image downloading and filtering (`download_images`).
- [ ] **Implement**: Image downloading logic with timeout and error handling.

### Phase 2: Gemini Client & Summarizer
- [ ] **Test**: Write tests for `backend/services/gemini.py` verifying `call_gemini_with_retry` properly handles a list of multimodal `contents` (text + images).
- [ ] **Implement**: Update `gemini.py` interfaces and logic.
- [ ] **Test**: Write tests for `backend/services/summarizer.py` verifying it constructs the correct multimodal prompt when `images` are provided.
- [ ] **Implement**: Update `summarizer.py` prompts and implementation to include image bytes.

### Phase 3: Pipeline Integration
- [ ] **Test**: Write tests for `backend/services/pipeline.py` verifying the new flow: RSS Collect -> Scrape -> Fetch Images -> Summarize (with Multimodal data). Verify fallback logic when scraping fails.
- [ ] **Implement**: Update `pipeline.py` to integrate the scraper and pass the downloaded image bytes down to the summarizer.
