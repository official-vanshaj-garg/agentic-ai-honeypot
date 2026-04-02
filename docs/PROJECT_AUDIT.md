# PROJECT AUDIT

**Audit date:** April 2026
**Codebase state:** Post-modular refactor. Previously a single 626-line `src/main.py`; now split into 12 files across `src/`.

---

## 1. Project Identity

| Field | Value |
|---|---|
| Name | NIRIKSHA.ai |
| Primary purpose | AI-powered honeypot: engage scammers, extract intelligence, generate reports |
| Scope | Backend REST API only. No database. No frontend. In-memory state. |
| Built for | India AI Impact Buildathon 2026 (HCL GUVI) |
| Classification | Research prototype. Not production-ready. |

---

## 2. Repository Layout

```
NIRIKSHA.ai/
├── src/
│   ├── main.py               App entry point (~20 lines)
│   ├── config.py             Env, Groq client, API key, delays, log_chat()
│   ├── schemas.py            Pydantic models
│   ├── session_state.py      6 global in-memory dicts
│   ├── utils/
│   │   ├── __init__.py
│   │   └── text.py           12 compiled regexes, word lists, helper functions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scoring.py        Scam signal scoring
│   │   ├── extraction.py     Intelligence extraction
│   │   ├── reply_generation.py  LLM reply, sanitisation, hint selection, guardrails
│   │   └── reporting.py      Scam classification, final report builder
│   ├── routes/
│   │   ├── __init__.py
│   │   └── detect.py         POST /api/detect handler
│   └── tests/
│       └── test_chat.py      Integration test: 5 scenarios
├── docs/
│   ├── OVERVIEW.md
│   ├── ARCHITECTURE.md
│   ├── CURRENT_STATUS.md
│   ├── FEATURE_MATRIX.md
│   ├── ROADMAP.md
│   └── PROJECT_AUDIT.md     (this file)
├── README.md
├── requirements.txt          fastapi, uvicorn, groq, pydantic, requests, python-dotenv
├── .env.example              GROQ_API_KEY, API_SECRET_KEY
└── .gitignore
```

---

## 3. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | |
| Framework | FastAPI | Async, auto-validates via Pydantic |
| LLM provider | Groq | Cloud inference. Free tier: 100k tokens/minute rate limit. |
| LLM model | Llama 3.3 70B (`llama-3.3-70b-versatile`) | Configurable via `GROQ_MODEL` env var |
| Validation | Pydantic v2 | |
| Server | uvicorn | ASGI |
| HTTP client | requests | Used only in `test_chat.py` |
| Env management | python-dotenv | |

---

## 4. Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Server crashes on startup if missing |
| `API_SECRET_KEY` | Yes | `""` | All requests return 403 if empty |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | |
| `MIN_HUMAN_DELAY_S` | No | `0.10` | |
| `MAX_HUMAN_DELAY_S` | No | `0.28` | |
| `PORT` | No | `8000` | |

---

## 5. Key Functions and Their Locations

| Function | File | Purpose |
|---|---|---|
| `log_chat()` | `src/config.py` | Print sender and message to stdout |
| `norm()` | `src/utils/text.py` | Lowercase + collapse whitespace |
| `_clean_url()` | `src/utils/text.py` | Strip trailing punctuation from URLs |
| `_normalize_phone()` | `src/utils/text.py` | Normalise to +91XXXXXXXXXX |
| `_has_digit()` | `src/utils/text.py` | Check if string contains a digit |
| `looks_like_payment_targeted()` | `src/services/scoring.py` | Detect payment-targeted messages |
| `calculate_scam_score()` | `src/services/scoring.py` | Cumulative scam signal score |
| `extract_intelligence()` | `src/services/extraction.py` | Core extraction (all 9 field types) |
| `high_value_count()` | `src/services/extraction.py` | Count non-empty high-value categories |
| `_count_features()` | `src/services/reply_generation.py` | Count rubric features in a reply text |
| `_sanitize_reply()` | `src/services/reply_generation.py` | Remove banned words, limit questions, cap length |
| `_next_hint()` | `src/services/reply_generation.py` | Pick next intel topic; mutates `SESSION_ASKED` |
| `_llm_generate_reply()` | `src/services/reply_generation.py` | Groq API call with system prompt |
| `_enforce_minimums()` | `src/services/reply_generation.py` | Force guardrail adjustments on designated turns |
| `infer_scam_type()` | `src/services/reporting.py` | LLM-based scam classification |
| `build_final_output()` | `src/services/reporting.py` | Assemble complete report dict |
| `detect_scam()` | `src/routes/detect.py` | Main endpoint handler; orchestrates everything |

---

## 6. Pydantic Models (`src/schemas.py`)

| Model | Purpose |
|---|---|
| `MessageItem` | A single message: `sender`, `text`, `timestamp` (all optional) |
| `IncomingRequest` | Full request payload. Accepts `sessionId`/`sessionld`/`session_id`, `conversationHistory`/`conversation_history`. Extra fields allowed. |
| `AgentResponse` | Response: `status`, `reply`, `finalCallback`, `finalOutput` |

---

## 7. Session State (`src/session_state.py`)

Six module-level objects. All importers share the same instances (Python module singleton pattern). Mutated in-place only — never reassigned.

| Object | Type | Written by |
|---|---|---|
| `SESSION_START_TIMES` | `Dict[str, float]` | `routes/detect.py` (init), `services/reporting.py` (read) |
| `SESSION_TURN_COUNT` | `Dict[str, int]` | `routes/detect.py` |
| `SESSION_SCAM_SCORE` | `Dict[str, int]` | `routes/detect.py` |
| `SESSION_COUNTS` | `Dict[str, Dict[str, int]]` | `routes/detect.py` |
| `SESSION_ASKED` | `Dict[str, Set[str]]` | `routes/detect.py`, `services/reply_generation._next_hint()` |
| `FINAL_REPORTED` | `Set[str]` | `routes/detect.py` |

---

## 8. Finalization Logic

Finalization triggers on a session when all of the following are satisfied:

```python
if session_id not in FINAL_REPORTED:
    hv = high_value_count(preview)
    enough_intel = (hv >= 2) and (len(preview.get("referenceIds", [])) >= 1)
    if turn >= 10 or (turn >= 8 and enough_intel):
        # trigger
```

When triggered:
1. `infer_scam_type()` makes a second Groq API call to classify the scam.
2. `build_final_output()` assembles the full report.
3. The session ID is added to `FINAL_REPORTED` so it only fires once.
4. The report is attached to the response as both `finalCallback` and `finalOutput`.

---

## 9. Security Assessment

| Aspect | Current State |
|---|---|
| Authentication | Single shared `API_SECRET_KEY`. No per-user auth. |
| Secrets | Loaded from `.env` (excluded from git via `.gitignore`). Server crashes on missing `GROQ_API_KEY`. |
| Input validation | Pydantic validates request structure; not content. |
| Input sanitisation | None. Raw text goes to regex and LLM prompt. |
| Rate limiting | None. |
| CORS | Not configured. |
| HTTPS | Not handled in application code. Must be terminated at the reverse proxy / platform level. |
| LLM prompt injection | Partially mitigated by system prompt rules. No input sanitisation. |
| Session memory | No bound on session dict growth. |

---

## 10. Known Honest Limitations

1. `scamDetected` is hardcoded `True` — never computed.
2. Engagement duration is artificially inflated for sessions with 16+ messages.
3. No persistence across restarts.
4. No retry on Groq API failure.
5. No unit tests. Integration tests only.
6. Phone extraction is India-specific.

---

## 11. Evaluation Results (Integration Test)

Run April 2026, local server, `src/tests/test_chat.py`:

| Scenario | Weight | Score |
|---|---|---|
| Bank Fraud | 25% | 97/100 |
| Phishing Link | 20% | 100/100 |
| Job Scam | 20% | 97/100 |
| Electricity Bill Scam | 20% | 100/100 |
| Investment Scam | 15% | ~99/100 |
| **Final** | | **96.65** |

Test scoring breakdown: Scam Detection (20pts), Extraction (30pts), Conversation Quality (30pts), Engagement (10pts), Structure (10pts).

---

## 12. Recommended Next Actions

In priority order:

1. Add session TTL and cleanup (prevent memory growth)
2. Add `GET /health` endpoint
3. Add CORS middleware
4. Add SQLite persistence for sessions and reports
5. Build a minimal frontend dashboard
6. Add rate limiting
7. Fix hardcoded `scamDetected: true`
8. Add structured logging
9. Add proper pytest unit tests
10. Add Dockerfile
