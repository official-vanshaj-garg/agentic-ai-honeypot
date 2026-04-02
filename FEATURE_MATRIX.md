# FEATURE MATRIX

| # | Feature | Status | Files Involved | Notes |
|---|---|---|---|---|
| 1 | POST /api/detect endpoint | **Implemented** | `src/main.py:543-619` | Full pipeline: auth, session, scoring, extraction, LLM reply, finalization |
| 2 | LLM reply generation | **Implemented** | `src/main.py:375-431` | Groq API, Llama 3.3 70B, system prompt with persona, temp 0.8, max 90 tokens |
| 3 | Scam signal scoring | **Implemented** | `src/main.py:159-191` | Regex-based. Scores OTP requests, payment pressure, urgency, links, phones, UPIs |
| 4 | Intelligence extraction (phones) | **Implemented** | `src/main.py:238-240, 102` | India-focused regex, +91 normalization |
| 5 | Intelligence extraction (bank accounts) | **Implemented** | `src/main.py:256-269` | 9-18 digit numbers, phone number dedup, epoch timestamp filtering |
| 6 | Intelligence extraction (UPI IDs) | **Implemented** | `src/main.py:243-254, 104` | Filters out emails and email prefixes |
| 7 | Intelligence extraction (phishing links) | **Implemented** | `src/main.py:235, 99` | HTTP/HTTPS URL regex with trailing punctuation cleanup |
| 8 | Intelligence extraction (emails) | **Implemented** | `src/main.py:236, 100` | Standard email regex |
| 9 | Intelligence extraction (reference IDs) | **Implemented** | `src/main.py:197-230` | REF, CASE, TICKET, ORDER, POLICY, etc. Split into caseIds, policyNumbers, orderNumbers |
| 10 | Deduplication | **Implemented** | `src/main.py:232-284` | Sets used for all categories; phone vs account overlap filtering |
| 11 | Multi-turn session management | **Implemented** | `src/main.py:50-55, 554-565` | In-memory dicts keyed by sessionId |
| 12 | Reply sanitization | **Implemented** | `src/main.py:305-327` | Removes banned words (honeypot, bot, ai, fraud, scam), limits to 1 question, 200 char cap |
| 13 | Rubric guardrail enforcement | **Implemented** | `src/main.py:433-448, 126` | Forces questions on turns {1,2,3,5,7} if below targets |
| 14 | Context-aware hint selection | **Implemented** | `src/main.py:329-373` | Prioritizes missing intel categories; adapts to KYC/UPI/payment context |
| 15 | Final report generation | **Implemented** | `src/main.py:502-537` | Triggered at turn >= 10 or turn >= 8 with enough intel |
| 16 | LLM scam type classification | **Implemented** | `src/main.py:454-500` | Separate Groq call, JSON parsing, fallback to "unknown" |
| 17 | API key authentication | **Implemented** | `src/main.py:30-31, 546-547` | x-api-key header vs API_SECRET_KEY env var |
| 18 | Human delay simulation | **Implemented** | `src/main.py:33-34, 569` | asyncio.sleep, configurable (0.10-0.28s) |
| 19 | Pydantic request validation | **Implemented** | `src/main.py:61-83` | Alias support for sessionId (3 forms), conversationHistory (2 forms), extra fields allowed |
| 20 | Test/evaluation harness | **Implemented** | `src/tests/test_chat.py` | 5 weighted scenarios, scoring for detection, extraction, quality, engagement, structure |
| 21 | Chat logging | **Partial** | `src/main.py:44-45` | `print()` to stdout only. No log files, no levels, no structured format |
| 22 | Error handling | **Partial** | `src/main.py:498-500, 588-589` | Try/except around LLM calls with fallback. No error tracking/reporting |
| 23 | Persistent storage / database | **Not implemented** | - | All state in-memory. Lost on restart |
| 24 | Frontend / dashboard | **Not implemented** | - | No UI exists |
| 25 | Rate limiting | **Not implemented** | - | No middleware or logic |
| 26 | Session cleanup / TTL | **Not implemented** | - | Memory grows unbounded |
| 27 | CORS configuration | **Not implemented** | - | No CORSMiddleware added |
| 28 | Containerization (Docker) | **Not implemented** | - | No Dockerfile |
| 29 | CI/CD pipeline | **Not implemented** | - | No GitHub Actions or similar |
| 30 | Unit tests (pytest) | **Not implemented** | - | test_chat.py is integration, not unit |
| 31 | Structured logging | **Not implemented** | - | No logging module usage |
| 32 | Webhook callback delivery | **Not implemented** | - | finalCallback returned in response, not POSTed |
| 33 | Multi-tenant auth | **Not implemented** | - | Single shared API key |
| 34 | Input sanitization | **Not implemented** | - | Raw text to regex and LLM |
| 35 | Health check endpoint | **Not implemented** | - | No GET / or /health route |
| 36 | Documentation (docs/) | **Not implemented** | `docs/` (empty) | Directory exists but is empty |

**Summary:** 20 features implemented, 2 partial, 14 not implemented.
