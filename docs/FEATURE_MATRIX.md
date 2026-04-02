# FEATURE MATRIX

Status values: **Implemented** | **Partial** | **Not implemented**

| # | Feature | Status | Primary File | Notes |
|---|---|---|---|---|
| 1 | `POST /api/detect` endpoint | **Implemented** | `src/routes/detect.py` | Full pipeline: auth → session → scoring → extraction → LLM reply → finalization |
| 2 | API key authentication | **Implemented** | `src/config.py`, `src/routes/detect.py` | `x-api-key` header vs `API_SECRET_KEY` env var |
| 3 | Multi-turn session management | **Implemented** | `src/session_state.py`, `src/routes/detect.py` | In-memory dicts keyed by `sessionId`. Lost on restart. |
| 4 | Scam signal scoring | **Implemented** | `src/services/scoring.py` | Regex-based, cumulative per session. Scores OTP requests, payment pressure, urgency, links, phones, UPIs. |
| 5 | Intelligence extraction — phones | **Implemented** | `src/services/extraction.py`, `src/utils/text.py` | India-focused regex; normalised to +91 format |
| 6 | Intelligence extraction — bank accounts | **Implemented** | `src/services/extraction.py` | 9–18 digit numbers; phone/UPI overlap removed; epoch timestamps excluded |
| 7 | Intelligence extraction — UPI IDs | **Implemented** | `src/services/extraction.py`, `src/utils/text.py` | Filtered to exclude email addresses and prefixes |
| 8 | Intelligence extraction — phishing links | **Implemented** | `src/services/extraction.py`, `src/utils/text.py` | HTTP/HTTPS URLs; trailing punctuation stripped |
| 9 | Intelligence extraction — email addresses | **Implemented** | `src/services/extraction.py`, `src/utils/text.py` | Standard email regex |
| 10 | Intelligence extraction — reference IDs | **Implemented** | `src/services/extraction.py`, `src/utils/text.py` | Prefixes: REF, CASE, TICKET, COMPLAINT, ORDER, POLICY, AWB, KYC, TXN, etc. Split into caseIds, policyNumbers, orderNumbers |
| 11 | Deduplication of extracted data | **Implemented** | `src/services/extraction.py` | Python sets for all categories; phone vs account overlap filtered |
| 12 | LLM reply generation | **Implemented** | `src/services/reply_generation.py` | Groq API, Llama 3.3 70B, temperature 0.8, max 90 tokens, last 8 turns as context |
| 13 | Reply sanitisation | **Implemented** | `src/services/reply_generation.py` | Removes banned words; ≤1 question; ≤200 characters |
| 14 | Context-aware hint topic selection | **Implemented** | `src/services/reply_generation.py` | Adapts topic order based on KYC/UPI/payment context; tracks which topics have been asked |
| 15 | Rubric guardrail enforcement | **Implemented** | `src/services/reply_generation.py` | Forces questions and investigative wording on turns {1,2,3,5,7} if below thresholds |
| 16 | Final report generation | **Implemented** | `src/services/reporting.py` | Triggered at turn ≥ 10, or turn ≥ 8 with ≥2 high-value fields and ≥1 reference ID |
| 17 | LLM scam type classification | **Implemented** | `src/services/reporting.py` | Separate Groq call; JSON parsed; falls back to `"unknown"` / 0.6 confidence |
| 18 | Human delay simulation | **Implemented** | `src/config.py`, `src/routes/detect.py` | `asyncio.sleep()` with configurable range; defaults 0.10–0.28s |
| 19 | Pydantic request validation | **Implemented** | `src/schemas.py` | Field aliases for `sessionId`, `conversationHistory`; extra fields allowed |
| 20 | Integration test harness | **Implemented** | `src/tests/test_chat.py` | 5 weighted scam scenarios; scores detection, extraction, quality, engagement, structure |
| 21 | Modular codebase | **Implemented** | All files under `src/` | Refactored from single 626-line file into config, schemas, session_state, utils, services, routes |
| 22 | Logging | **Partial** | `src/config.py` | `print()` to stdout only; no log files, no levels, no structured format |
| 23 | Error handling | **Partial** | `src/services/reply_generation.py`, `src/services/reporting.py` | `try/except` around Groq calls; fallback reply; no error tracking or notification |
| 24 | Persistent storage | **Not implemented** | — | All state in-memory; lost on restart |
| 25 | Session cleanup / TTL | **Not implemented** | — | Memory grows without bound; no expiry mechanism |
| 26 | Frontend / dashboard | **Not implemented** | — | No UI; API-only |
| 27 | Rate limiting | **Not implemented** | — | No middleware or logic |
| 28 | CORS configuration | **Not implemented** | — | No `CORSMiddleware`; browser clients blocked |
| 29 | Health check endpoint | **Not implemented** | — | No `GET /health` or root route |
| 30 | Multi-tenant authentication | **Not implemented** | — | Single shared `API_SECRET_KEY` |
| 31 | Webhook / push delivery | **Not implemented** | — | `finalCallback` returned in response body; not pushed to a URL |
| 32 | Unit tests (pytest) | **Not implemented** | — | `test_chat.py` is integration-only; requires a running server |
| 33 | Structured logging | **Not implemented** | — | No `logging` module usage |
| 34 | Containerisation (Docker) | **Not implemented** | — | No Dockerfile |
| 35 | CI/CD pipeline | **Not implemented** | — | No GitHub Actions or equivalent |
| 36 | Input sanitisation | **Not implemented** | — | Raw text goes to regex and LLM prompt |
| 37 | ML-based entity extraction | **Not implemented** | — | Extraction is regex-only |
| 38 | Multi-language support | **Not implemented** | — | Prompts and phone patterns are English/India-specific |

**Summary:** 21 implemented, 2 partial, 15 not implemented.
