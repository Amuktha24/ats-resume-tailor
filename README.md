# ATS Resume Tailor

A full-stack web app that takes a job description and a current resume and produces a tailored, ATS-friendly PDF. The backend uses Anthropic Claude Sonnet 4.5 to rewrite the resume and convert it to LaTeX, then renders it via Overleaf.

## Stack

- Frontend: React + Tailwind CSS + Framer Motion (dark editorial UI)
- Backend: FastAPI (Python)
- LLM: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) via Emergent integrations
- PDF rendering: Overleaf (authenticated HTTP)

## Environment variables

Set these in `/app/backend/.env` (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `EMERGENT_LLM_KEY` | Emergent Universal LLM key (used by default) |
| `ANTHROPIC_API_KEY` | Optional direct Anthropic key (overrides Emergent key) |
| `OVERLEAF_SESSION_COOKIE` | Raw value of the `overleaf_session2` cookie |
| `OVERLEAF_GCLB_TOKEN` | Raw value of the `GCLB` cookie |
| `MONGO_URL` / `DB_NAME` | Pre-provisioned by Emergent; leave as-is |

## Features
- Tailors resumes to job descriptions using Claude
- Converts optimized resume content into LaTeX
- Creates an editable Overleaf project
- Compiles and returns a downloadable PDF
- Keeps resume and job description data in memory only

## How It Works
1. User pastes a job description and current resume
2. Claude rewrites the resume for ATS alignment
3. Claude converts the resume into LaTeX
4. Backend creates and compiles an Overleaf project
5. User downloads the final PDF or opens the project in Overleaf

### How to refresh Overleaf cookies

1. Log in to https://www.overleaf.com in a regular browser tab.
2. Open DevTools -> Application -> Cookies -> `https://www.overleaf.com`.
3. Copy the raw value of the cookies named `overleaf_session2` and `GCLB`.
4. Paste them into `/app/backend/.env` as `OVERLEAF_SESSION_COOKIE` and `OVERLEAF_GCLB_TOKEN`.
5. Restart the backend: `sudo supervisorctl restart backend`.

Cookies expire periodically, so refresh them when you see "Overleaf session expired" errors.

## Endpoints

- `GET /api/health` - config status
- `POST /api/generate` - body `{ "jobDescription": string, "currentResume": string }`, returns `{ status, projectUrl, pdfUrl, pdfBase64 }`

The endpoint is rate-limited to 10 requests per IP per hour. Resume and JD text are never logged or persisted.
