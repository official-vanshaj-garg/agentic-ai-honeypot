# PROJECT AUDIT: NIRIKSHA.ai (Agentic AI Honeypot)

**Audit Date:** 2026-03-17
**Audited By:** Automated Codebase Audit
**Repository Root:** `Agentic AI Honeypot/`

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Name** | NIRIKSHA.ai |
| **Purpose** | An AI-powered honeypot that engages scammers in multi-turn conversations using LLM-generated replies, silently extracts scam intelligence (phone numbers, UPI IDs, bank accounts, phishing links, etc.), and produces structured final reports. |
| **Problem** | Traditional anti-scam systems block fraudsters immediately, gaining no intelligence. NIRIKSHA.ai keeps scammers talking to extract actionable data. |
| **Scope** | Backend API only. Single endpoint. In-memory session state. No persistent storage, no frontend, no dashboard. |
| **Classification** | **Research prototype / Hackathon submission** (built for India AI Impact Buildathon 2026). Not production-ready. |

---

## 2. Architecture

### System Workflow (single request)

```
1. Scammer POST /api/detect with sessionId, message, conversationHistory
2. API key validation (x-api-key header vs API_SECRET_KEY env var)
3. Session initialization or retrieval (in-memory dicts)
4. Scam signal scoring (regex-based, cumulative per session)
5. Intelligence extraction from full conversation text (regex-based)
6. Determine "next hint" topic for LLM (what intel to ask for next)
7. LLM reply generation via Groq API (Llama 3.3 70B)
8. Reply sanitization (banned words removal, question limit, length cap)
9. Rubric guardrail enforcement (force questions on certain turns)
10. Finalization check (turn >= 10, or turn >= 8 with enough intel)
11. If finalizing: LLM-based scam type classification, build report
12. Return JSON: { status, reply, finalCallback?, finalOutput? }
```

### High-Level Components (all in `src/main.py`)

| Section | Lines | Purpose |
|---|---|---|
| Config | 17-37 | Load env vars, init Groq client, FastAPI app |
| Chat Logging | 41-45 | Simple `print()` logger |
| Session State | 47-55 | In-memory dicts for session tracking |
| Pydantic Models | 57-91 | `MessageItem`, `IncomingRequest`, `AgentResponse` |
| Normalization & Patterns | 93-126 | Regex patterns for URL, email, phone, UPI, OTP, references |
| Scam Score | 144-191 | Rule-based scam signal scoring |
| Intelligence Extraction | 193-290 | Regex-based extraction of phones, accounts, UPIs, links, emails, reference IDs |
| LLM Reply Generation | 292-448 | Groq API call with system prompt, rubric guardrails, sanitization |
| Final Output | 450-537 | LLM-based scam classification, report builder |
| API Endpoint | 539-619 | `POST /api/detect` handler |
| Server Runner | 621-626 | `uvicorn.run()` entry point |

### Entry Points

- **API:** `POST /api/detect` (line 543)
- **Direct run:** `python src/main.py` starts uvicorn on `0.0.0.0:PORT` (line 625-626)
- **Module run:** `uvicorn src.main:app` (documented in README)

---

## 3. Tech Stack

| Category | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | Single file, ~626 lines |
| Framework | FastAPI | Async REST API with auto-validation |
| LLM Provider | Groq | Cloud inference API |
| LLM Model | Llama 3.3 70B (`llama-3.3-70b-versatile`) | Configurable via `GROQ_MODEL` env var |
| Validation | Pydantic v2 | Request/response schemas with alias support |
| HTTP Client | requests | Used only in test file |
| Env Config | python-dotenv | Loads `.env` file |
| Server | uvicorn | ASGI server |
| Deployment | Railway | Cloud hosting (per README) |

### Dependencies (`requirements.txt`)

```
fastapi
uvicorn
requests
python-dotenv
groq
pydantic
```

### Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** | None (crashes if missing) | Groq API authentication |
| `API_SECRET_KEY` | **Yes** | `""` (all requests return 403 if empty) | API key for `x-api-key` header |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | LLM model to use |
| `MIN_HUMAN_DELAY_S` | No | `0.10` | Minimum simulated human delay |
| `MAX_HUMAN_DELAY_S` | No | `0.28` | Maximum simulated human delay |
| `PORT` | No | `8000` | Server port |

---

## 4. Code Structure

### File Map

```
Agentic AI Honeypot/
├── src/
│   ├── main.py              # ENTIRE backend logic (626 lines, 22.7 KB)
│   └── tests/
│       └── test_chat.py     # Interactive scenario evaluator (321 lines, 9.7 KB)
├── docs/                    # EMPTY directory
├── README.md                # Detailed documentation (445 lines, 14.1 KB)
├── requirements.txt         # 6 dependencies
├── .env.example             # 2 env vars template
└── .gitignore               # Standard Python ignores
```

### Key Functions in `src/main.py`

| Function | Line | Purpose |
|---|---|---|
| `norm(text)` | 96-97 | Normalize text (lowercase, collapse whitespace) |
| `_clean_url(u)` | 128-129 | Strip trailing punctuation from URLs |
| `_normalize_phone(p)` | 131-139 | Normalize Indian phone numbers to `+91XXXXXXXXXX` |
| `looks_like_payment_targeted(text)` | 148-157 | Detect payment-targeted scam attempts |
| `calculate_scam_score(text)` | 159-191 | Compute cumulative scam score from message text |
| `_extract_reference_ids(text)` | 197-214 | Extract reference/case/ticket/order IDs via regex |
| `_split_ids(ids)` | 216-230 | Categorize extracted IDs into caseIds, policyNumbers, orderNumbers |
| `extract_intelligence(history, latest_text)` | 232-284 | **Core extraction**: phones, bank accounts, UPIs, links, emails, reference IDs from full conversation |
| `high_value_count(extracted)` | 286-290 | Count how many high-value intel categories have data |
| `_count_features(text)` | 296-303 | Count rubric features (questions, investigative, red flags, elicitation) |
| `_sanitize_reply(reply)` | 305-327 | Remove banned words, limit questions to 1, cap length at 200 chars |
| `_next_hint(session_id, incoming_text, preview)` | 329-373 | Determine next topic for LLM to ask about (missing intel) |
| `_llm_generate_reply(...)` | 375-431 | Generate reply via Groq API with system prompt and rubric guidance |
| `_enforce_minimums(turn, reply, counts)` | 433-448 | Force investigative questions on designated turns if below rubric targets |
| `infer_scam_type(history, latest_text)` | 454-500 | LLM-based scam classification (returns type + confidence) |
| `build_final_output(session_id, history, latest_text)` | 502-537 | Build complete final report JSON |
| `detect_scam(payload, api_key_token)` | 544-619 | **Main endpoint handler**: orchestrates the full pipeline |
| `log_chat(sender, text)` | 44-45 | Print chat messages to stdout |

### Key Classes / Models

| Class | Line | Purpose |
|---|---|---|
| `MessageItem` | 61-64 | Schema for a single conversation message |
| `IncomingRequest` | 67-83 | Request payload with alias support for `sessionId`, `conversationHistory` |
| `AgentResponse` | 86-90 | Response schema: `status`, `reply`, `finalCallback`, `finalOutput` |

### Session State (Global Dicts)

| Variable | Type | Purpose |
|---|---|---|
| `SESSION_START_TIMES` | `Dict[str, float]` | Unix timestamp when session started |
| `SESSION_TURN_COUNT` | `Dict[str, int]` | Number of scammer messages received |
| `SESSION_SCAM_SCORE` | `Dict[str, int]` | Cumulative scam score |
| `SESSION_COUNTS` | `Dict[str, Dict[str, int]]` | Running rubric feature counts (q, inv, rf, eli) |
| `SESSION_ASKED` | `Dict[str, Set[str]]` | Which hint topics have been asked |
| `FINAL_REPORTED` | `Set[str]` | Sessions that have already received final report |

---

## 5. Feature Matrix

| Feature | Status | Files | Notes |
|---|---|---|---|
| Scam detection (signal scoring) | **Implemented** | `src/main.py:159-191` | Regex-based, cumulative per session. Not ML-based. |
| Multi-turn conversation handling | **Implemented** | `src/main.py:543-619` | Via in-memory session dicts. No persistence across restarts. |
| LLM reply generation | **Implemented** | `src/main.py:375-431` | Groq API, system prompt with persona, rubric guidance, temperature 0.8 |
| Reply sanitization | **Implemented** | `src/main.py:305-327` | Banned word removal, single question enforcement, 200-char cap |
| Intelligence extraction (regex) | **Implemented** | `src/main.py:232-284` | Phones, bank accounts, UPIs, links, emails, reference IDs |
| Deduplication | **Implemented** | `src/main.py:232-284` | Uses sets for all extracted fields; phone/UPI vs email overlap filtering |
| Final report generation | **Implemented** | `src/main.py:502-537` | Triggered at turn 10 (or turn 8 with enough intel) |
| LLM scam type classification | **Implemented** | `src/main.py:454-500` | Separate Groq call with JSON output parsing, fallback to "unknown" |
| API key authentication | **Implemented** | `src/main.py:30-31, 546-547` | `x-api-key` header checked against `API_SECRET_KEY` env var |
| Human delay simulation | **Implemented** | `src/main.py:33-34, 569` | Configurable async sleep (0.10-0.28s default) |
| Rubric guardrail enforcement | **Implemented** | `src/main.py:433-448` | Forces questions on turns {1,2,3,5,7} if below rubric targets |
| Next-hint topic selection | **Implemented** | `src/main.py:329-373` | Context-aware ordering of missing intel prompts |
| Test/evaluation harness | **Implemented** | `src/tests/test_chat.py` | 5 scenarios, weighted scoring, local evaluation |
| Chat logging | **Partial** | `src/main.py:44-45` | `print()` only. No log files, no structured logging, no log levels. |
| Persistent storage (DB) | **Not implemented** | - | All data in-memory. Lost on restart. |
| Dashboard / Frontend | **Not implemented** | - | No HTML, no UI. API-only. |
| Rate limiting | **Not implemented** | - | No rate limiting on the endpoint. |
| Session cleanup / TTL | **Not implemented** | - | Sessions accumulate forever in memory until process restart. |
| User registration / multi-tenant auth | **Not implemented** | - | Single shared API key only. |
| Webhook / callback delivery | **Not implemented** | - | `finalCallback` is returned in the response, not POSTed to a callback URL. |
| Unit tests (pytest) | **Not implemented** | - | `test_chat.py` is an integration test runner, not pytest. |
| CI/CD pipeline | **Not implemented** | - | No GitHub Actions, no Dockerfile, no CI config. |
| Containerization | **Not implemented** | - | No Dockerfile. |
| Input sanitization / XSS protection | **Not implemented** | - | Raw text passed directly to regex and LLM. |
| Structured logging / audit trail | **Not implemented** | - | No structured logs. Just stdout prints. |
| CORS configuration | **Not implemented** | - | No CORS middleware configured. |
| Documentation (docs/) | **Not implemented** | - | `docs/` directory is empty. README mentions a `.pptx` but it's not present. |

---

## 6. Inputs and Outputs

### API Request Schema

```json
{
  "sessionId": "string (also accepts sessionld, session_id)",
  "message": {
    "sender": "string",
    "text": "string",
    "timestamp": "string | number"
  },
  "conversationHistory": [
    {
      "sender": "string",
      "text": "string",
      "timestamp": "string | number"
    }
  ],
  "metadata": { "optional": "dict" }
}
```

**Flexibility:** Also accepts flat `sender` and `text` fields at the root level. `session_id` accepts three alias variations.

### API Response Schema

```json
{
  "status": "success",
  "reply": "string (the honeypot's response)",
  "finalCallback": null | { /* final report object */ },
  "finalOutput": null | { /* same as finalCallback */ }
}
```

### Final Report Schema (returned in `finalCallback` / `finalOutput`)

```json
{
  "sessionId": "string",
  "status": "completed",
  "scamDetected": true,
  "totalMessagesExchanged": "integer",
  "engagementDurationSeconds": "integer",
  "scamType": "bank_fraud|upi_fraud|phishing|job_scam|investment_scam|lottery_scam|kyc_scam|utility_scam|unknown",
  "confidenceLevel": "float (0-1)",
  "extractedIntelligence": {
    "phoneNumbers": ["string"],
    "bankAccounts": ["string"],
    "upiIds": ["string"],
    "phishingLinks": ["string"],
    "emailAddresses": ["string"],
    "caseIds": ["string"],
    "policyNumbers": ["string"],
    "orderNumbers": ["string"],
    "referenceIds": ["string"]
  },
  "engagementMetrics": {
    "totalMessagesExchanged": "integer",
    "engagementDurationSeconds": "integer"
  },
  "agentNotes": "string"
}
```

---

## 7. Data and Persistence

| Aspect | Status |
|---|---|
| Storage mechanism | **In-memory Python dicts** |
| Database | **None** |
| Persistence across restarts | **None** - all session data is lost |
| What is persisted | Nothing |
| What should be persisted | Sessions, extracted intelligence, final reports, conversation logs |
| File-based storage | Not used |
| Data export | Only via API response at finalization time |

---

## 8. Security and Robustness

| Aspect | Status | Notes |
|---|---|---|
| Authentication | API key header (`x-api-key`) | Single shared key. No per-user auth. |
| Secrets handling | `.env` file via `python-dotenv` | `.env` in `.gitignore`. Crashes if `GROQ_API_KEY` missing. |
| Input validation | Pydantic v2 models | Validates structure, not content. |
| XSS / Injection | **Not handled** | Raw text goes to regex and LLM. |
| Rate limiting | **Not implemented** | No protection against abuse. |
| CORS | **Not configured** | Will block browser-based requests. |
| Error handling | Broad `try/except` in LLM calls | Falls back to static reply. No error logging. |
| Session cleanup | **Not implemented** | Memory leaks with many sessions. |
| LLM prompt injection | **Partially mitigated** | System prompt has strict rules, but no input sanitization. |
| HTTPS | Via Railway deployment | Not handled in app code. |

### Known Risks

1. **Memory leak**: Session dicts grow unbounded. No TTL, no cleanup.
2. **Single point of failure**: One Groq API key, one model. No retry logic.
3. **No rate limiting**: Endpoint can be abused.
4. **Scam score always positive**: `scamDetected` is hardcoded to `True` in final output (line 520).
5. **Duration inflation**: If `totalMessagesExchanged >= 16`, duration is artificially inflated to `181+ seconds` (line 512-513).

---

## 9. Setup and Run Instructions

### Working Setup Steps

```bash
# 1. Clone
git clone https://github.com/ABHI99RAJPUT/NIRIKSHA.ai.git
cd NIRIKSHA.ai

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure .env
# Copy .env.example to .env and fill in:
#   GROQ_API_KEY=your_groq_key
#   API_SECRET_KEY=your_api_key

# 5. Run server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
# OR
python src/main.py

# 6. Test
# Edit API_KEY in src/tests/test_chat.py
python src/tests/test_chat.py
```

### Missing / Broken Steps

- No `Dockerfile` or container instructions
- No instructions for Railway deployment config
- `docs/NIRIKSHA.ai - Team Brats.pptx` is mentioned in README but file does not exist in `docs/`
- No pytest setup. `test_chat.py` requires a running server.

---

## 10. Current Progress Status

### What Is Working

- Full multi-turn conversation pipeline via `POST /api/detect`
- LLM-powered reply generation with persona and rubric awareness
- Regex-based intelligence extraction (9 field categories)
- Scam signal scoring
- Final report generation with LLM scam classification
- API key authentication
- Human delay simulation
- Test harness with 5 scam scenarios

### What Is Demo-Ready

- The API endpoint (local or Railway)
- Multi-turn scam engagement flow
- Final report output
- Test evaluation with scoring

### What Is Unfinished

- No persistent storage
- No frontend/dashboard
- No containerization
- No CI/CD
- No structured logging
- No rate limiting
- No session cleanup
- Empty `docs/` directory
- Missing pitch deck file

### Biggest Blockers

1. No database means intelligence is lost on every restart
2. No frontend means no visual demo beyond API calls
3. Single-file architecture limits maintainability

### Most Important Next Steps

1. Add database (SQLite or PostgreSQL) for session and intelligence persistence
2. Build a minimal dashboard to visualize conversations and extracted data
3. Refactor `main.py` into modules (routes, services, models, extraction, config)
4. Add Dockerfile for consistent deployment
5. Add rate limiting middleware
6. Add structured logging
7. Write proper pytest unit tests
8. Add session TTL / cleanup

---

## 11. Research / Product Angle

### Research Paper Viability

| Aspect | Assessment |
|---|---|
| Core idea | **Strong** - agentic honeypot with LLM engagement is novel and publishable |
| Technical depth | **Moderate** - regex extraction + LLM generation is a reasonable pipeline |
| Evaluation | **Partial** - `test_chat.py` provides a scoring framework but it's self-evaluation, not independent |
| Missing for paper | Dataset of real scam conversations, comparison with baselines, IRB/ethics consideration, quantitative metrics beyond self-scoring |
| State of art comparison | Not present |
| Novelty claim | LLM-generated persona for scammer engagement + silent extraction is the novel contribution |

### MVP / Product Viability

| Aspect | Assessment |
|---|---|
| Core value | Clear and demonstrated |
| Missing for MVP | Database, dashboard, multi-tenant auth, rate limiting, monitoring |
| Deployment | Works on Railway but lacks production hardening |
| Scalability | In-memory state limits to single instance |
| Business model | Potential as SaaS for banks/telcos, but far from production-ready |

### What Looks Strong

- The system prompt engineering for maintaining a believable persona
- The rubric-aware reply generation that naturally hits evaluation targets
- The context-aware "next hint" system for eliciting missing intelligence
- The comprehensive extraction pipeline covering 9 field types

### What Needs Improvement

- Architecture (single file, no separation of concerns)
- Persistence (none)
- Testing (integration only, no unit tests)
- Security hardening
- Observability (no logging, no metrics)
