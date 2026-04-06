# AI HANDOFF DOCUMENT

**Last updated:** April 2026

---

## 1. Project Title

**NIRIKSHA.ai: Agentic AI Honeypot for Scam Detection, Engagement, and Intelligence Extraction**

---

## 2. Project Summary

This is a Python/FastAPI backend that acts as an AI-powered honeypot. When a scammer sends a message, the system pretends to be a confused but cooperative person using an LLM (Llama 3.3 70B via Groq API). It maintains a multi-turn conversation, silently extracts identifying information (phone numbers, UPI IDs, bank accounts, phishing links, email addresses, reference IDs) using regex, and after approximately 10 turns produces a structured intelligence report with an LLM-based scam type classification. All conversations and extracted indicators are persisted in a local SQLite database. There is no frontend. The project was built for the India AI Impact Buildathon 2026 and is classified as a research prototype.

---

## 3. Current Project Goal

The core API pipeline is complete and tested. The next goal is to build a web-based dashboard (chat view, intelligence panel, report card) so the project can be demonstrated visually for academic and hackathon presentation.

---

## 4. Current Technical Status

| Area | Status |
|---|---|
| API pipeline | **Working** — tested, scoring 100/100 aggregate (98.00 final) |
| Database persistence | **Working** — SQLite via SQLModel |
| Retrieval endpoints | **Working** — 4 authenticated GET routes |
| Modular codebase | **Done** — split into config, schemas, session_state, utils, services, routes, models, db |
| Frontend / dashboard | **Not started** |
| Deployment | **Local only** — no hosting configured |
| CI/CD | **Not implemented** |
| Unit tests (pytest) | **Not implemented** — integration test harness only |

---

## 5. Current Working Features

- `POST /api/detect` endpoint — full scam engagement pipeline
- Multi-turn session management (in-memory dicts + SQLite persistence)
- LLM reply generation via Groq API (Llama 3.3 70B), persona-driven
- Regex-based scam signal scoring (cumulative per session)
- Regex-based intelligence extraction: phone numbers, bank accounts, UPI IDs, phishing links, emails, case IDs, policy numbers, order numbers, reference IDs
- Deduplication and normalisation of all extracted data
- Reply sanitisation (banned words, single-question limit, 200-char cap)
- Rubric-aware guardrail enforcement on designated turns
- Context-aware hint topic selection (asks for missing intel naturally)
- Final report generation with LLM scam type classification
- API key authentication (`x-api-key` header)
- Human delay simulation (configurable async sleep)
- SQLite persistence for sessions, messages, indicators, and reports
- Indicator upsert with `hit_count` tracking across distinct sessions
- Authenticated read-only retrieval endpoints:
  - `GET /api/sessions` — all sessions, sorted by last update
  - `GET /api/sessions/{session_id}` — session detail + messages + indicators
  - `GET /api/reports/{session_id}` — parsed final report
  - `GET /api/indicators` — all indicators sorted by hit count
- Integration test harness with 5 weighted scam scenarios

---

## 6. Partial / Unfinished Features

| Feature | What exists | What is missing |
|---|---|---|
| Logging | `print()` statements to stdout | Structured logging with levels, file output, timestamps |
| Error handling | `try/except` around Groq API calls with fallback | No error tracking, no alerting, no logging of failure cause |
| `scamDetected` field | Always hardcoded to `True` | Should be computed from actual scam score |
| Engagement duration | Artificially inflated for 16+ message sessions | Should use real duration only |

---

## 7. Current Database Status

**Engine:** SQLite, file at `data/agentic_ai_honeypot.db`
**ORM:** SQLModel (Pydantic + SQLAlchemy hybrid)
**Tables:** 5

| Table | Purpose | Key columns |
|---|---|---|
| `session` | One row per conversation | `id` (PK, session_id string), `turn_count`, `scam_score`, 4 rubric fields, `asked_hints`, `status` |
| `message` | Every message (scammer + honeypot) | `session_id` (FK), `sender`, `text`, `turn_number` |
| `indicator` | Global unique indicator registry | `indicator_type`, `value` (unique pair), `hit_count`, `first_seen_at`, `last_seen_at` |
| `session_indicator` | Links indicators to sessions | `session_id` + `indicator_id` (unique pair) |
| `report` | Final report per session | `session_id` (FK, unique), `scam_type`, `confidence`, `full_report_json` |

**Indicator types stored:** `phone`, `bank_account`, `upi`, `phishing_link`, `email`, `reference_id`

**How it works:** The in-memory session dicts (in `src/session_state.py`) remain the primary data layer for each request. DB writes happen after each in-memory update as fire-and-forget calls wrapped in `try/except`. If the DB fails, the API still works. The DB is populated by helper functions in `src/db.py` called from `src/routes/detect.py`.

**Retrieval endpoints** in `src/routes/retrieval.py` read directly from the DB. They are authenticated with the same `x-api-key` mechanism as the POST endpoint.

---

## 8. Current API / Backend Status

**Framework:** FastAPI
**Endpoints:**
- `POST /api/detect` — scam engagement pipeline
- `GET /api/sessions` — list all sessions
- `GET /api/sessions/{session_id}` — session detail with messages and indicators
- `GET /api/reports/{session_id}` — final report for a session
- `GET /api/indicators` — all unique indicators

**Auth:** All endpoints require `x-api-key` header matching `API_SECRET_KEY` env var

**Request shape (POST /api/detect):**
```json
{
  "sessionId": "string",
  "message": { "sender": "scammer", "text": "string", "timestamp": "string" },
  "conversationHistory": [ { "sender": "...", "text": "...", "timestamp": "..." } ],
  "metadata": {}
}
```

**Response shape (turns 1-9):**
```json
{
  "status": "success",
  "reply": "string",
  "finalCallback": null,
  "finalOutput": null
}
```

**Response shape (finalization, turn 10+):**
`finalCallback` and `finalOutput` contain the full intelligence report as a dict.

**Error codes:** 403 (bad API key), 404 (session/report not found, GET only), 422 (malformed body, POST only)

**No CORS middleware** configured yet. Browser-based clients cannot reach the API directly.

---

## 9. Current Docs Status

| File | Content |
|---|---|
| `README.md` | Main entry point — overview, setup, API docs, structure, limitations, team |
| `docs/OVERVIEW.md` | Purpose, audience, novelty, positioning |
| `docs/ARCHITECTURE.md` | System flow, module breakdown, API schemas, import graph |
| `docs/CURRENT_STATUS.md` | What works, partial, missing, test scores |
| `docs/FEATURE_MATRIX.md` | 38-row feature table with status and file references |
| `docs/ROADMAP.md` | 6-phase future development plan |
| `docs/PROJECT_AUDIT.md` | Technical audit of the codebase |
| `docs/DB_PLAN.md` | Database integration plan (already implemented) |
| `docs/AI_HANDOFF.md` | This file |
| `docs/archive/` | Old pre-refactor versions of audit and feature docs |

---

## 10. Exact Repository Structure

```
Agentic AI Honeypot/
├── src/
│   ├── __init__.py
│   ├── main.py                  # App entry point: FastAPI app, router, create_db()
│   ├── config.py                # Env vars, Groq client, API key, delays, log_chat()
│   ├── schemas.py               # Pydantic models: MessageItem, IncomingRequest, AgentResponse
│   ├── session_state.py         # 6 in-memory dicts (module-level singletons)
│   ├── models.py                # SQLModel table classes (5 tables)
│   ├── db.py                    # SQLite engine, create_db(), 5 DB helper functions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── detect.py            # POST /api/detect handler (orchestrates full pipeline + DB writes)
│   │   └── retrieval.py         # GET /api/sessions, sessions/{id}, reports/{id}, indicators (read-only, authenticated)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scoring.py           # calculate_scam_score(), looks_like_payment_targeted()
│   │   ├── extraction.py        # extract_intelligence(), high_value_count()
│   │   ├── reply_generation.py  # LLM reply, sanitisation, hint selection, guardrails
│   │   └── reporting.py         # infer_scam_type(), build_final_output()
│   ├── utils/
│   │   ├── __init__.py
│   │   └── text.py              # 12 compiled regexes, word lists, norm(), phone normalisation
│   └── tests/
│       └── test_chat.py         # Integration test: 5 scam scenarios with weighted scoring
├── data/
│   └── agentic_ai_honeypot.db   # SQLite database (auto-created on startup, gitignored)
├── docs/                        # All documentation files
├── requirements.txt             # fastapi, uvicorn, requests, python-dotenv, groq, pydantic, sqlmodel
├── .env.example                 # Template: GROQ_API_KEY, API_SECRET_KEY
├── .gitignore                   # Ignores .env, venv, __pycache__, data/, *.db
└── README.md
```

---

## 11. Key Files and What They Do

| File | Role | Safety note |
|---|---|---|
| `src/routes/detect.py` | **The most important file.** Orchestrates the full request pipeline: auth, session init, scoring, extraction, LLM reply, sanitisation, guardrails, finalization, DB writes. | Changes here can break the API and the test score. |
| `src/routes/retrieval.py` | Read-only GET endpoints for sessions, reports, and indicators. Uses router-level auth dependency. | Safe to modify. Does not affect POST /api/detect or test scores. |
| `src/services/reply_generation.py` | System prompt, LLM call, rubric guidance. Controls the persona and reply quality. | Changes here directly affect the test score (96-99/100). |
| `src/services/extraction.py` | Regex-based intelligence extraction (9 field types). | Changes here affect what intel gets extracted and stored. |
| `src/services/reporting.py` | Final report builder and LLM scam classification. | Changes here affect the `finalCallback` response shape. |
| `src/services/scoring.py` | Regex scam signal scoring. | Changes affect risk assessment. Low impact on test score. |
| `src/session_state.py` | 6 module-level dicts. All importers share the same objects. | Never reassign these dicts, only mutate them. |
| `src/models.py` | SQLModel table definitions for the 5 DB tables. | Changing field names/types breaks the DB without migration. |
| `src/db.py` | SQLite engine + 5 helper functions for DB writes. | All helpers are wrapped in try/except. DB failures don't crash the API. |
| `src/config.py` | Env vars, Groq client init. | Crashes on startup if `GROQ_API_KEY` is missing. |
| `src/schemas.py` | Pydantic request/response models with field aliases. | Changes here break the API contract. |
| `src/utils/text.py` | Compiled regexes, banned word list, phone normalisation. | Changes here affect extraction and scoring. |
| `src/tests/test_chat.py` | 5-scenario integration test. Requires a running server and matching API key. | Do not modify unless adding new scenarios. |

---

## 12. What Must Not Be Changed Casually

1. **Response shape** of `POST /api/detect` — the test harness and any future evaluator depend on it.
2. **System prompt** in `src/services/reply_generation.py` — small changes can tank the test score.
3. **Extraction regexes** in `src/utils/text.py` and `src/services/extraction.py` — these are tuned to the test scenarios.
4. **Finalization logic** in `src/routes/detect.py` (lines deciding when to trigger final report) — tested to work at turn 10, or turn 8+ with enough intel.
5. **Session state dicts** in `src/session_state.py` — never reassign them, only mutate in-place.
6. **DB table definitions** in `src/models.py` — renaming fields or changing types will break the existing DB without Alembic migrations (not installed).
7. **`API_SECRET_KEY`** in `.env` must match the `API_KEY` in `src/tests/test_chat.py` for tests to pass.

---

## 13. How to Run the Project Locally

```bash
# Prerequisites: Python 3.10+, a free Groq API key from console.groq.com/keys

# 1. Clone and enter directory
git clone https://github.com/ABHI99RAJPUT/NIRIKSHA.ai.git
cd NIRIKSHA.ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file with two required variables:
#    GROQ_API_KEY=your_groq_key
#    API_SECRET_KEY=any_password_you_choose
# API_SECRET_KEY is a password you set yourself. It is not from Groq.

# 5. Start the server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# The server creates data/agentic_ai_honeypot.db automatically on startup.
# Local endpoint: http://127.0.0.1:8000/api/detect
```

---

## 14. How to Test It

```bash
# The server must be running first.
# Edit API_KEY in src/tests/test_chat.py to match your API_SECRET_KEY.
python src/tests/test_chat.py
```

This runs 5 scam scenarios (Bank Fraud, Phishing Link, Job Scam, Electricity Bill, Investment Scam) with weighted scoring. Expected aggregate score: 96-99/100.

**Last verified score:** 100/100 aggregate, 98.00 final (April 2026, with DB persistence and retrieval endpoints active).

---

## 15. Current Known Issues / Limitations

1. `scamDetected` is hardcoded to `True` in every final report. It never returns `False`.
2. Engagement duration is artificially padded to 181+ seconds for sessions with 16+ messages.
3. Session dicts (`SESSION_START_TIMES`, etc.) grow without bound in memory. No TTL or cleanup.
4. No retry logic for Groq API calls. A transient failure returns a static fallback reply with no logging.
5. No CORS middleware. Browser-based clients cannot reach the API.
6. No health check endpoint (`GET /health`).
7. Phone extraction is India-specific (10-digit numbers starting with 6-9, +91 prefix).
8. Extraction is regex-only. No ML-based entity recognition.
9. `test_chat.py` requires manual API key update and a running server.
10. No Alembic. Changing DB table definitions requires manually deleting the `.db` file.

---

## 16. Best Next Development Step

**Build a web-based dashboard** that reads from the existing retrieval endpoints and displays:

1. **Session list** — all sessions with status, scam type, turn count
2. **Chat view** — conversation replay for any selected session
3. **Intelligence panel** — extracted indicators for a session
4. **Report card** — final report display

The retrieval API already exists (`GET /api/sessions`, `/sessions/{id}`, `/reports/{id}`, `/indicators`).

Before building the frontend:
1. Add CORS middleware to `src/main.py` (required for any browser-based client)
2. Build the frontend (recommended: plain HTML/CSS/JS served from FastAPI for simplicity, or a separate Vite/React app for a richer UI)

This step does not touch scoring, extraction, reply generation, or the `POST /api/detect` endpoint.

---

## 17. Network Security Academic Relevance

This project is relevant to a **Network Security** course because:

- **Honeypot concept**: The system is a honeypot — a deliberately exposed system designed to attract attackers and gather intelligence about their methods and infrastructure.
- **Threat intelligence extraction**: The system extracts indicators of compromise (IOCs) — phone numbers, UPI IDs, phishing links, bank accounts — which are standard threat intelligence artifacts in cybersecurity.
- **Social engineering defence**: The project demonstrates how AI can be used defensively against social engineering attacks (scam calls/messages), which is a core network security topic.
- **Active defence / deception**: Rather than passively blocking, the system actively engages the attacker to waste their time and gather data. This is an emerging area in security research.
- **Repeated threat correlation**: The `hit_count` tracking across sessions demonstrates how indicators can be correlated to identify persistent threat infrastructure.

Suggested academic framing: "AI-Assisted Active Defence and Threat Intelligence Gathering Using LLM-Powered Honeypots"

---

## 18. Product / Research Relevance

| Track | Assessment |
|---|---|
| **Hackathon** | Complete and working. Scored 100/100 aggregate on built-in evaluation. |
| **College mini-project** | Suitable. Core pipeline works, architecture is clean, codebase is modular. |
| **Research paper** | Core idea is novel and publishable. Missing: real scam dataset, baseline comparison, independent evaluation, ethics review. |
| **Product / SaaS** | Not ready. Missing: frontend, multi-tenant auth, rate limiting, production DB, monitoring, deployment. |

---

## 19. Safe Instructions for the Next AI Assistant

If you are an AI assistant continuing work on this project, follow these rules:

1. **Read first.** Before modifying any code, read the file you plan to change AND `src/routes/detect.py` to understand the full request flow.
2. **Do not touch scoring, extraction, reply generation, or reporting logic** unless the user specifically asks you to change those and understands the risk to test scores.
3. **Always preserve the response shape** of `POST /api/detect`. The `AgentResponse` schema in `src/schemas.py` must not change.
4. **The in-memory session dicts and the DB run in parallel.** In-memory is the primary data layer during a request. DB writes are secondary. Do not remove the in-memory layer.
5. **DB writes are fire-and-forget.** They are wrapped in `try/except` in `src/db.py`. DB failures must never crash the API.
6. **Test after every change** by running `python src/tests/test_chat.py`. If the score drops significantly below 96, you broke something.
7. **The `.env` file contains `GROQ_API_KEY` and `API_SECRET_KEY`.** The `API_SECRET_KEY` is a password the user chose. It is not from any external service. The `API_KEY` in `test_chat.py` must match it.
8. **If adding new endpoints**, put them in `src/routes/` and register the router in `src/main.py`. Do not put route logic in `src/main.py` directly.
9. **If adding frontend code**, keep it separate from `src/`. A `frontend/` or `static/` directory at the project root is appropriate.
10. **If changing DB schema**, delete `data/agentic_ai_honeypot.db` so it gets recreated with the new schema on next startup. There is no Alembic migration system.
11. **Environment variables:**
    - `GROQ_API_KEY` (required, from Groq console)
    - `API_SECRET_KEY` (required, user-chosen password)
    - `GROQ_MODEL` (optional, default: `llama-3.3-70b-versatile`)
    - `MIN_HUMAN_DELAY_S` / `MAX_HUMAN_DELAY_S` (optional, default: 0.10 / 0.28)
    - `PORT` (optional, default: 8000)
12. **Dependencies:** fastapi, uvicorn, requests, python-dotenv, groq, pydantic, sqlmodel. Do not add heavy frameworks without reason.
