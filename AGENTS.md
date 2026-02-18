# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI application code.
  - `routers/` for HTTP endpoints, `services/` for business logic, `schemas/` for Pydantic models.
- `frontend/src/`: React + Vite client app.
  - `pages/`, `components/`, `hooks/`, `api/`, `types/`, `mocks/` (MSW handlers/data).
- `tests/`: Python `pytest` suite.
- `frontend/e2e/`: Playwright end-to-end specs.
- `docs/`: design plans, migration notes, and operational docs.

## Build, Test, and Development Commands
- `uv sync`: install Python dependencies.
- `uv run uvicorn backend.main:app --reload`: run backend locally.
- `cd frontend && npm install && npm run dev`: run frontend locally (MSW enabled by default).
- `VITE_ENABLE_MSW=false npm run dev` (in `frontend/`): run frontend against real backend.
- `uv run pytest -q`: run backend tests.
- `cd frontend && npx playwright test`: run e2e tests.
- `cd frontend && npm run lint`: run frontend lint checks.
- `uv run pre-commit run --all-files`: run full repository quality gate.

## Coding Style & Naming Conventions
- Python: 4-space indentation, explicit type hints, snake_case for functions/modules, PascalCase for classes.
- TypeScript/React: functional components in PascalCase, hooks prefixed with `use`, file names aligned with exported symbol (e.g., `Digest.tsx`, `useDigest.ts`).
- Keep API route prefixes stable (e.g., `/api/digests`) and centralize data access in `services/`.
- Tooling: Ruff + mypy for Python, ESLint + TypeScript compiler for frontend.

## Testing Guidelines
- Backend tests use `pytest`; new tests go under `tests/test_*.py`.
- E2E tests use Playwright; place specs in `frontend/e2e/*.spec.ts`.
- Add or update tests with each behavior change; verify both happy path and failure/edge cases.

## Commit & Pull Request Guidelines
- Follow conventional prefixes seen in history: `feat:`, `fix:`, `refactor:`, `test(e2e):`, `docs:`.
- Keep commit messages in English and scope each commit to one logical change.
- PRs should include:
  - concise summary of behavior changes,
  - verification commands executed,
  - links to related plan/issues,
  - screenshots or recordings for visible UI changes.

## Security & Configuration Tips
- Do not commit secrets; keep credentials in root `.env`.
- Required local keys include Supabase and Gemini settings.
- Prefer testing auth-protected routes with valid JWTs; avoid bypassing auth logic in production code.
