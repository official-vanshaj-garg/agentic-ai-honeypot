# STATUS FOR AI ASSISTANT

> Use this document to quickly understand the NIRIKSHA.ai project as it exists right now.

---

## Project Name

**NIRIKSHA.ai** (also referred to as "Agentic AI Honeypot")

## What the Project Does

NIRIKSHA.ai is an AI-powered honeypot backend that:
1. Receives scam messages via a REST API
2. Maintains multi-turn conversations using LLM-generated replies (Groq + Llama 3.3 70B)
3. Silently extracts scam intelligence (phone numbers, bank accounts, UPI IDs, phishing links, emails, reference IDs) from the conversation using regex
4. Produces a structured final report after ~10 conversation turns

The system pretends to be a confused, cooperative person to keep scammers engaged.

## Current Objective

This was built for the **India AI Impact Buildathon 2026** (HCL GUVI). The current objective is a working API that can engage scammers, extract intelligence, and produce reports. It is designed to be evaluated by an automated evaluator that sends scam messages and scores responses.

## Main Workflow

```
Scammer message --> API key check --> Session init/update --> Scam score calculation
--> Intelligence extraction (regex) --> Next-hint topic selection --> LLM reply generation
--> Reply sanitization --> Rubric guardrail check --> Finalization check
--> Return { status: "success", reply: "...", finalCallback: ... }
```

## Implemented Features

- [x] Single POST endpoint (`/api/detect`) with full request/response pipeline
- [x] LLM reply generation via Groq API (Llama 3.3 70B)
- [x] System prompt with believable persona (confused, cooperative person)
- [x] Scam signal scoring (regex-based, cumulative)
- [x] Intelligence extraction: phones, bank accounts, UPI IDs, links, emails, case IDs, policy numbers, order numbers, reference IDs
- [x] Deduplication of extracted data
- [x] Phone number normalization (Indian format)
- [x] UPI vs email disambiguation
- [x] Epoch timestamp filtering for bank accounts
- [x] Reply sanitization (banned words, question limit, length cap)
- [x] Rubric-aware reply generation (questions, investigative wording, red flags, elicitation)
- [x] Context-aware next-hint topic selection
- [x] Final report generation with LLM scam classification
- [x] API key authentication (x-api-key header)
- [x] Human delay simulation
- [x] Pydantic request/response validation with alias support
- [x] Test harness with 5 scam scenarios and weighted scoring

## Partial Features

- [~] Logging: `print()` statements only. No structured logging, no log files, no log levels.
- [~] Error handling: Broad try/except around LLM calls with fallback reply. No error tracking.

## Missing Features

- [ ] Database / persistent storage (all data in-memory, lost on restart)
- [ ] Frontend / dashboard
- [ ] Rate limiting
- [ ] Session cleanup / TTL (memory leak with many sessions)
- [ ] Multi-tenant authentication (single shared API key)
- [ ] CORS configuration
- [ ] Containerization (no Dockerfile)
- [ ] CI/CD pipeline
- [ ] Unit tests (pytest)
- [ ] Structured logging / audit trail
- [ ] Webhook / callback delivery
- [ ] Input sanitization (XSS protection)
- [ ] Monitoring / metrics
- [ ] Documentation in docs/ folder (currently empty)

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Framework | FastAPI |
| LLM | Groq API + Llama 3.3 70B Versatile |
| Validation | Pydantic v2 |
| Server | uvicorn |
| Deployment | Railway |
| Dependencies | fastapi, uvicorn, requests, python-dotenv, groq, pydantic |

## Database / Storage Status

**No database.** All session state stored in Python dicts in memory:
- `SESSION_START_TIMES`, `SESSION_TURN_COUNT`, `SESSION_SCAM_SCORE`, `SESSION_COUNTS`, `SESSION_ASKED`, `FINAL_REPORTED`
- Data is completely lost on process restart.

## API / Backend Status

**Working.** Single endpoint `POST /api/detect` handles the full pipeline. Deployed on Railway.

## Frontend / Dashboard Status

**Does not exist.** No HTML, no UI. Interaction is API-only.

## Security Status

- API key auth: implemented (single shared key)
- Secrets: `.env` file, `.gitignore` excludes it
- No rate limiting
- No CORS
- No input sanitization
- `scamDetected` is hardcoded to `True` (line 520 of main.py)
- Engagement duration artificially inflated for 16+ message sessions (line 512-513)

## Known Issues

1. Session dicts grow unbounded (memory leak)
2. `scamDetected` hardcoded to `True` - never returns `False`
3. Engagement duration inflated artificially when messages >= 16
4. Single Groq API key with no retry/failover logic
5. `docs/` folder is empty; README references a `.pptx` that doesn't exist
6. `test_chat.py` requires manual API key update and a running server
7. No way to retrieve past session data (no persistence)

## Immediate Next Steps

1. Add SQLite/PostgreSQL for session + intelligence persistence
2. Refactor `main.py` into separate modules (routes, services, models, extraction)
3. Add Dockerfile
4. Build a basic dashboard (view conversations, extracted data, reports)
5. Add rate limiting middleware
6. Add proper pytest tests
7. Add structured logging

## Suggested Project Title Based on Actual Implementation

> **"NIRIKSHA.ai: An LLM-Powered Agentic Honeypot for Multi-Turn Scam Engagement and Intelligence Extraction"**
