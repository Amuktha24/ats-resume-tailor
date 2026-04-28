"""
ATS Resume Tailor - FastAPI backend.

Flow for POST /api/generate:
  1. Claude #1: rewrite the resume for ATS, output markdown.
  2. Claude #2: convert markdown resume -> LaTeX using a fixed template.
  3. Overleaf: fetch CSRF token.
  4. Overleaf: POST /docs with LaTeX, capture new projectId from redirect.
  5. Overleaf: POST /project/<id>/compile -> returns outputFiles JSON.
  6. Download output.pdf, base64-encode, return to frontend.
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import time
import uuid
import logging
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, Optional
from urllib.parse import unquote

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from emergentintegrations.llm.chat import LlmChat, UserMessage

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ats_resume_tailor")

app = FastAPI(title="ATS Resume Tailor")
api_router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Rate limiting - 10 requests per IP per hour, in-memory
# ---------------------------------------------------------------------------
_RATE_LIMIT_WINDOW = 3600  # seconds
_RATE_LIMIT_MAX = 10
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    bucket = _rate_buckets[ip]
    while bucket and now - bucket[0] > _RATE_LIMIT_WINDOW:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again in an hour.",
        )
    bucket.append(now)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    jobDescription: str = Field(..., min_length=1)
    currentResume: str = Field(..., min_length=1)


class GenerateResponse(BaseModel):
    status: str
    projectUrl: Optional[str] = None
    pdfUrl: Optional[str] = None
    pdfBase64: Optional[str] = None
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Prompts (verbatim from problem statement)
# ---------------------------------------------------------------------------
REWRITER_SYSTEM_PROMPT = """## **Refined Prompt: ATS-Optimized Resume Rewriter**

You are an expert resume writer and ATS optimization specialist.

Your task is to generate a **completely new, ATS-optimized resume** using two inputs:

1. **Job Description**
2. **Current Resume**

---

## **Inputs**

**Job Description:**
{JOB_DESCRIPTION}

**Current Resume:**
{CURRENT_RESUME}

---

## **Core Objective**

Transform the provided resume into a **highly targeted, keyword-optimized resume** that aligns strongly with the given job description and skills.

The output must:
* Maximize **ATS keyword matching**
* Improve **clarity, impact, and structure**
* Present **experience in a results-driven, achievement-oriented way**

---

## **Execution Guidelines**

### Step 1: Extract Structured Data
From the current resume, extract only factual information (do NOT reuse phrasing):
* Personal details: Name, Address, Phone, Email, LinkedIn, GitHub
* Education: Degree, Institution, Location, Dates
* Work Experience: Company names, job titles, dates
* Projects (if present)

### Step 2: Keyword & Skill Mapping
From the job description and skills:
* Identify **primary keywords** (core skills, tools, technologies)
* Identify **secondary keywords** (soft skills, domain knowledge, methodologies)
* Identify **action verbs and impact phrases**

### Step 3: Resume Reconstruction
Build a completely new resume with these rules:
1. **No Reuse of Original Language** - do NOT copy or paraphrase sentences; only reuse raw facts.
2. **Strong Keyword Integration** - weave JD keywords naturally into summary, skills, and bullets.
3. **Work Experience Enhancement** - each bullet: strong action verb + JD tools/tech + measurable impact.
4. **Professional Summary** - 3-5 lines, role-aligned, impact-focused.
5. **Skills Section** - grouped by category; JD-relevant skills first.
6. **Clarity & Readability** - clean, concise, consistent.

---

## **Output Format (Strictly Follow)**

---

**[Full Name]**

**Address:** [Full Address]

**Phone No:** [Phone Number] | **Email:** [Email Address] | **LinkedIn:** [LinkedIn URL] | **GitHub:** [GitHub URL]

---

### **Professional Summary**
[ATS-optimized, role-aligned summary]

---

### **Education**
**[Degree]**
[College Name] | [Location] | [Start Date] - [End Date]

---

### **Work Experience**
**[Company Name] | [Location] | [Job Title]** | [Start Date] - [End Date]
* [Achievement-driven bullet with keywords + impact]
* [Achievement-driven bullet with keywords + impact]
* [Achievement-driven bullet with keywords + impact]

---

### **Skills**
* **[Category]:** [Relevant skills]

---

### **Projects**
**[Project Title]**
* [Description with tools, keywords, and measurable impact]

---

## **Critical Constraints**
* Do NOT include explanations, notes, or commentary.
* Do NOT output anything outside the defined format.
* Do NOT miss important keywords from the job description.
* Do NOT keyword-stuff unnaturally - maintain readability.
"""


LATEX_SYSTEM_PROMPT = r"""You are an expert LaTeX developer specializing in professional resume formatting. Convert the plain text resume below into valid, compile-ready LaTeX code using the predefined template.

Resume text:
```
{MARKDOWN_RESUME}
```

### Rules
1. Do not modify the template structure - keep all commands, environments, and sections intact.
2. Only populate content fields: Name, Contact, Education, Work Experience, Projects, Skills, Certifications, Achievements.
3. Preserve LaTeX formatting, spacing, and list environments.
4. Escape special characters: % $ & _ # { } ~ ^ \
5. Do not hallucinate - only use info from the resume text.
6. Latest experience first.
7. Output ONLY the final LaTeX code - no explanations, no markdown code fences.

### Strict Requirements
* Summary: 1 line max.
* Each experience: max 3 most-relevant bullets.
* Keep only ONE project.
* Achievements section should highlight big wins and relevant certifications.

### Compilation Rules (Non-Negotiable)
* Must compile with pdflatex with zero errors/warnings.
* No undefined commands or custom macros.
* Escape all LaTeX special characters.

### Output MUST follow this exact template structure - fill in the fields, keep the skeleton:

%-------------------------------------------
\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{fontawesome5}

\definecolor{light-grey}{gray}{0.83}
\definecolor{dark-grey}{gray}{0.3}
\definecolor{text-grey}{gray}{.20}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{0in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{\bfseries\vspace{2pt}\raggedright\large}{}{0em}{}[{\color{light-grey}\titlerule[1pt]}\vspace{-4pt}]

\newcommand{\resumeItem}[1]{\item\small{#1 \vspace{-2pt}}}

\newcommand{\resumeSubheading}[4]{%
  \vspace{-1pt}\item
    \begin{tabular*}{\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & {\color{dark-grey}\small #2} \\
      \textit{\small #3} & {\color{dark-grey}\small #4} \\
    \end{tabular*}\vspace{-4pt}%
}

\newcommand{\resumeProjectHeading}[2]{%
    \item
    \begin{tabular*}{\textwidth}{l@{\extracolsep{\fill}}r}
      #1 & {\color{dark-grey}\small #2} \\
    \end{tabular*}\vspace{-4pt}%
}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-4pt}}

\color{text-grey}

\begin{document}

%----------HEADING----------
\begin{center}
    \textbf{\Huge [FULL NAME]} \\ \vspace{5pt}
    \small \faPhone* \ [PHONE] \hspace{2pt}$|$\hspace{2pt}
    \faEnvelope \ [EMAIL] \hspace{2pt}$|$\hspace{2pt}
    \faLinkedin \ [LINKEDIN] \hspace{2pt}$|$\hspace{2pt}
    \faGithub \ [GITHUB] \hspace{2pt}$|$\hspace{2pt}
    \faMapMarker* \ [LOCATION]
\end{center}

\section{SUMMARY}
[One-line summary]

\section{EDUCATION}
  \resumeSubHeadingListStart
    \resumeSubheading
      {[University]}{[Dates]}
      {[Degree, GPA]}{[Location]}
  \resumeSubHeadingListEnd

\section{EXPERIENCE}
  \resumeSubHeadingListStart
    \resumeSubheading
      {[Company]}{[Dates]}
      {[Title]}{[Location]}
      \resumeItemListStart
        \resumeItem{[Bullet 1]}
        \resumeItem{[Bullet 2]}
        \resumeItem{[Bullet 3]}
      \resumeItemListEnd
  \resumeSubHeadingListEnd

\section{PROJECTS}
  \resumeSubHeadingListStart
    \resumeProjectHeading
      {\textbf{[Project Title]}}{[Dates]}
      \resumeItemListStart
        \resumeItem{[Bullet]}
      \resumeItemListEnd
  \resumeSubHeadingListEnd

\section{SKILLS}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
     \textbf{[Category 1]}: [skills] \\
     \textbf{[Category 2]}: [skills]
    }}
 \end{itemize}

\section{ACHIEVEMENTS}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
     \textbf{[Achievement]}: [detail]
    }}
 \end{itemize}

\end{document}
"""


# ---------------------------------------------------------------------------
# Claude helpers
# ---------------------------------------------------------------------------
def _get_llm_key() -> str:
    # Prefer user-provided Anthropic key, fallback to Emergent universal key
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured.")
    return key


async def _call_claude(system_prompt: str, user_text: str, max_tokens: int) -> str:
    key = _get_llm_key()
    chat = (
        LlmChat(
            api_key=key,
            session_id=str(uuid.uuid4()),
            system_message=system_prompt,
        )
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
        .with_params(max_tokens=max_tokens)
    )
    message = UserMessage(text=user_text)
    response = await chat.send_message(message)
    if not isinstance(response, str):
        response = str(response)
    return response.strip()


# ---------------------------------------------------------------------------
# Overleaf pipeline
# ---------------------------------------------------------------------------
OVERLEAF_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _overleaf_cookies() -> str:
    session = os.environ.get("OVERLEAF_SESSION_COOKIE", "")
    gclb = os.environ.get("OVERLEAF_GCLB_TOKEN", "")
    if not session:
        raise HTTPException(
            status_code=500,
            detail="Overleaf credentials not configured. Please set environment variables.",
        )
    session = unquote(session)
    cookie = f"overleaf_session2={session}"
    if gclb:
        cookie += f"; GCLB={gclb}"
    return cookie


def _fetch_csrf(cookie_header: str) -> str:
    resp = requests.get(
        "https://www.overleaf.com/project",
        headers={"User-Agent": OVERLEAF_UA, "Cookie": cookie_header},
        timeout=30,
        allow_redirects=True,
    )
    # If we ended up on /login, the session cookie is invalid/expired.
    if "/login" in resp.url:
        raise HTTPException(
            status_code=401,
            detail=(
                "Overleaf session cookie is not authenticated. "
                "Log in to overleaf.com, then copy a fresh `overleaf_session2` "
                "value from DevTools > Application > Cookies."
            ),
        )
    html = resp.text
    match = re.search(r'name="ol-csrfToken" content="([^"]+)"', html) or re.search(
        r'content="([^"]+)" name="ol-csrfToken"', html
    )
    if not match:
        raise HTTPException(
            status_code=500,
            detail="Overleaf session expired. Please refresh your session cookie.",
        )
    return match.group(1)


def _create_project(latex_code: str, csrf: str, cookie_header: str) -> str:
    resp = requests.post(
        "https://www.overleaf.com/docs",
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.overleaf.com/project",
            "Origin": "https://www.overleaf.com",
            "User-Agent": OVERLEAF_UA,
            "Cookie": cookie_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"_csrf": csrf, "snip": latex_code, "engine": "pdflatex"},
        allow_redirects=False,
        timeout=60,
    )
    location = resp.headers.get("Location", "")
    pid_match = re.search(r"/project/([a-f0-9]{24})", location)
    if not pid_match:
        raise HTTPException(
            status_code=502,
            detail="Failed to create Overleaf project (no project ID returned).",
        )
    return pid_match.group(1)


def _compile_project(project_id: str, csrf: str, cookie_header: str) -> dict:
    resp = requests.post(
        f"https://www.overleaf.com/project/{project_id}/compile",
        headers={
            "Cookie": cookie_header,
            "X-Csrf-Token": csrf,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": OVERLEAF_UA,
        },
        data={"check": "silent", "draft": "true", "stopOnFirstError": "false"},
        timeout=120,
    )
    try:
        return resp.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail=f"Overleaf compile returned non-JSON: {exc}"
        ) from exc


def _download_pdf(pdf_url: str, cookie_header: str) -> bytes:
    resp = requests.get(
        pdf_url,
        headers={"Cookie": cookie_header, "User-Agent": OVERLEAF_UA},
        timeout=120,
    )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to download PDF from Overleaf (status {resp.status_code}).",
        )
    return resp.content


def _run_overleaf_pipeline(latex_code: str) -> dict:
    cookie_header = _overleaf_cookies()
    csrf = _fetch_csrf(cookie_header)
    project_id = _create_project(latex_code, csrf, cookie_header)
    project_url = f"https://www.overleaf.com/project/{project_id}"
    compile_resp = _compile_project(project_id, csrf, cookie_header)

    output_files = compile_resp.get("outputFiles") or []
    pdf_file = next((f for f in output_files if f.get("path") == "output.pdf"), None)
    if not pdf_file:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Overleaf compile did not produce a PDF. "
                f"Open {project_url} to view the compilation log."
            ),
        )
    pdf_url = "https://www.overleaf.com" + pdf_file["url"]
    pdf_bytes = _download_pdf(pdf_url, cookie_header)
    return {
        "projectUrl": project_url,
        "pdfUrl": pdf_url,
        "pdfBase64": base64.b64encode(pdf_bytes).decode("ascii"),
    }


def _clean_latex(raw: str) -> str:
    cleaned = re.sub(r"^```latex\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"service": "ATS Resume Tailor", "status": "ok"}


@api_router.get("/health")
async def health():
    return {
        "status": "ok",
        "anthropicConfigured": bool(
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
        ),
        "overleafConfigured": bool(os.environ.get("OVERLEAF_SESSION_COOKIE")),
    }


@api_router.post("/generate", response_model=GenerateResponse)
async def generate_resume(payload: GenerateRequest, request: Request):
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    _check_rate_limit(client_ip)

    # Fail fast on missing Overleaf session so we don't burn Claude tokens.
    # GCLB is optional - only required in some regions.
    if not os.environ.get("OVERLEAF_SESSION_COOKIE"):
        raise HTTPException(
            status_code=500,
            detail="Overleaf credentials not configured. Please set environment variables.",
        )

    try:
        # Step 1 - ATS rewrite
        rewriter_prompt = REWRITER_SYSTEM_PROMPT.replace(
            "{JOB_DESCRIPTION}", payload.jobDescription
        ).replace("{CURRENT_RESUME}", payload.currentResume)
        markdown_resume = await _call_claude(
            system_prompt=rewriter_prompt,
            user_text="Generate the ATS-optimized resume now.",
            max_tokens=4096,
        )
        logger.info("Claude rewrite complete (%d chars)", len(markdown_resume))

        # Step 2 - LaTeX conversion
        latex_prompt = LATEX_SYSTEM_PROMPT.replace("{MARKDOWN_RESUME}", markdown_resume)
        latex_raw = await _call_claude(
            system_prompt=latex_prompt,
            user_text="Output the final LaTeX now. No fences, no commentary.",
            max_tokens=8192,
        )
        latex_code = _clean_latex(latex_raw)
        # Debug: persist the last generated LaTeX (no PII unless DEBUG_LATEX=1)
        if os.environ.get("DEBUG_LATEX") == "1":
            try:
                Path("/tmp/last_resume.tex").write_text(latex_code)
            except Exception:  # noqa: BLE001
                pass
        logger.info("LaTeX generated (%d chars)", len(latex_code))

        # Steps 3-7 - Overleaf pipeline (blocking I/O, offload to thread)
        result = await asyncio.to_thread(_run_overleaf_pipeline, latex_code)
        logger.info("Overleaf pipeline complete: %s", result["projectUrl"])

        return GenerateResponse(status="success", **result)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_resume failed")
        return GenerateResponse(status="error", message=str(exc))


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
