# ATS Resume Tailor - PRD

## Original problem statement
Full-stack web app "ATS Resume Tailor" that takes a Job Description and a Current Resume, calls Anthropic Claude (`claude-sonnet-4-5-20250929`) to rewrite the resume and convert it to LaTeX, then renders it to a PDF via scraping Overleaf's authenticated HTTP endpoints. Dark-themed React landing page with hero, how-it-works, and a generator form. Single `POST /api/generate` endpoint implementing 7 sequential steps.

## Architecture
- **Backend**: FastAPI (Python) at `/app/backend/server.py`, single route `POST /api/generate`, uses `emergentintegrations.llm.chat.LlmChat` with model `claude-sonnet-4-5-20250929` (2 sequential calls), then `requests` library for the Overleaf pipeline (CSRF fetch -> POST /docs -> compile -> download PDF).
- **Frontend**: React 19 + Tailwind + Framer Motion at `/app/frontend/src/App.js`. Dark editorial theme, Clash Display headings + Geist body + Geist Mono for textareas, electric indigo (#4F46E5) accent.
- **DB**: MongoDB connected but unused per privacy requirement (in-memory processing only).
- **Rate limiting**: in-memory sliding window, 10 req/IP/hr.

## User personas
- Job seekers who want a recruiter-ready, ATS-optimized PDF for a specific role without manual rewriting.

## Core requirements (static)
1. Two text inputs: Job Description + Current Resume.
2. Outputs a downloadable `tailored_resume.pdf` and an Overleaf project link.
3. No persistence of resume/JD data to disk, DB, or logs.
4. Configurable via env: `EMERGENT_LLM_KEY` or `ANTHROPIC_API_KEY`, `OVERLEAF_SESSION_COOKIE`, `OVERLEAF_GCLB_TOKEN`.

## Implemented (2026-02)
- Backend `POST /api/generate` with 7-step pipeline (Claude rewrite -> Claude LaTeX -> CSRF -> create project -> compile -> download -> base64). Fail-fast when Overleaf creds missing (saves Claude tokens).
- `GET /api/health` diagnostics endpoint.
- Rate limiting (10/IP/hr), no logging of user text, `.env.example` and `README.md` shipped.
- Frontend landing page: sticky nav, animated hero (grid + radial), 3-card how-it-works, side-by-side 320px-min textareas, generate button with faux-streaming status messages ("Analyzing..." -> "Rewriting..." -> "Converting..." -> "Compiling..." -> "Done!"), success card with Download + Open in Overleaf, red error card with Retry, minimal footer.
- All interactive elements carry `data-testid`.
- Testing: iteration_1 100% pass on backend + frontend.

## Backlog / remaining work
**P0 (blocking for live happy path):**
- User must populate `OVERLEAF_SESSION_COOKIE` and `OVERLEAF_GCLB_TOKEN` in `/app/backend/.env` (cookies expire; refresh when seeing "Overleaf session expired" errors).

**P1:**
- End-to-end verification of LaTeX template once real Overleaf cookies are available; template has some brace imbalances in the system prompt that may need tweaking if Overleaf compile fails.
- Convert rate limiter to Redis/Mongo to survive backend restarts and multi-worker.
- Real SSE streaming instead of client-side faux progression, so status messages reflect actual backend progress.

**P2:**
- Support PDF/DOCX resume upload (text extraction).
- Save recent generations client-side (localStorage) for quick re-edit.
- Rich side-by-side diff view: original vs tailored.
