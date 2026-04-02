# ARCHITECTURE

This document describes how the system works, how the code is organised, and how data flows through a single request.

---

## System Flow (Single Request)

```
Client sends POST /api/detect
  │
  ├─ 1. API key check (x-api-key header vs API_SECRET_KEY)
  │       → 403 if mismatch
  │
  ├─ 2. Parse request (Pydantic)
  │       sessionId, message.text, conversationHistory
  │
  ├─ 3. Session init or resume
  │       In-memory dicts keyed by sessionId
  │       Initialised on first turn; incremented on each subsequent turn
  │
  ├─ 4. Scam signal scoring
  │       Regex-based, cumulative across session
  │       Scores OTP requests, payment pressure, urgency words, links, phones, UPIs
  │
  ├─ 5. Intelligence extraction
  │       Runs on full conversation text (history + current message)
  │       Extracts: phones, bank accounts, UPI IDs, phishing links,
  │                 emails, case IDs, policy numbers, order numbers, reference IDs
  │       Deduplicates using sets; filters phone/UPI/email overlaps
  │
  ├─ 6. Next-hint selection
  │       Determines which intel category is still missing
  │       Adapts order based on message context (KYC → link; payment → UPI)
  │
  ├─ 7. LLM reply generation (Groq / Llama 3.3 70B)
  │       System prompt: persona as confused, cooperative person
  │       Guided by hint topic and current rubric feature counts
  │       Last 8 conversation turns passed as context
  │
  ├─ 8. Reply sanitisation
  │       Remove banned words: honeypot, bot, ai, fraud, scam
  │       Limit to one question mark
  │       Cap at 200 characters
  │
  ├─ 9. Rubric guardrail enforcement
  │       On designated turns (1, 2, 3, 5, 7): force a question if below target
  │       Force investigative wording if below target
  │
  ├─ 10. Finalization check
  │        Trigger if: turn ≥ 10, OR (turn ≥ 8 AND ≥2 high-value fields AND ≥1 reference ID)
  │        If triggered:
  │          → LLM call to classify scam type + confidence
  │          → Build full intelligence report
  │          → Add to response as finalCallback + finalOutput
  │
  └─ 11. Return AgentResponse
           { status, reply, finalCallback, finalOutput }
```

---

## Module Breakdown

After refactoring from a single 626-line file, the codebase is split into:

```
src/
├── main.py               Entry point. Creates FastAPI app, mounts router, runs uvicorn.
├── config.py             Loads .env. Initialises Groq client, API key header, delay
│                         constants, PORT, log_chat().
├── schemas.py            Pydantic models:
│                           MessageItem — one message in a conversation
│                           IncomingRequest — full request payload (with field aliases)
│                           AgentResponse — response schema
├── session_state.py      Six module-level dicts/sets that hold all in-memory state.
│                         These are Python module singletons — all importers share
│                         the same objects. Never reassigned; only mutated.
│
├── utils/
│   └── text.py           12 compiled regex patterns (URL, email, phone, UPI, OTP,
│                         PIN, reference IDs, etc.), word lists (BANNED_WORDS,
│                         RED_FLAG_WORDS, etc.), QUESTION_TURNS constant,
│                         norm(), _clean_url(), _normalize_phone(), _has_digit()
│
├── services/
│   ├── scoring.py        looks_like_payment_targeted(), calculate_scam_score()
│   │                     Uses patterns from utils/text.py. No external calls.
│   │
│   ├── extraction.py     _extract_reference_ids(), _split_ids(),
│   │                     extract_intelligence(), high_value_count()
│   │                     Pure regex over concatenated conversation text.
│   │
│   ├── reply_generation.py
│   │                     _count_features() — counts rubric features in a reply
│   │                     _sanitize_reply() — removes banned words, limits questions
│   │                     _next_hint() — picks next intel topic; mutates SESSION_ASKED
│   │                     _llm_generate_reply() — Groq API call with system prompt
│   │                     _enforce_minimums() — guardrail for designated turns
│   │
│   └── reporting.py      infer_scam_type() — second Groq call, JSON output, fallback
│                         build_final_output() — assembles the full report dict
│                         Reads SESSION_START_TIMES for duration calculation.
│
└── routes/
    └── detect.py         detect_scam() — the single route handler on APIRouter.
                          Orchestrates the full pipeline. Reads/writes all 6 state dicts.
```

---

## Session State

Six module-level objects in `src/session_state.py`:

| Object | Type | Purpose |
|---|---|---|
| `SESSION_START_TIMES` | `Dict[str, float]` | Unix timestamp of session start |
| `SESSION_TURN_COUNT` | `Dict[str, int]` | Number of scammer turns received |
| `SESSION_SCAM_SCORE` | `Dict[str, int]` | Cumulative regex scam score |
| `SESSION_COUNTS` | `Dict[str, Dict[str, int]]` | Rubric feature counts per session (q, inv, rf, eli) |
| `SESSION_ASKED` | `Dict[str, Set[str]]` | Which hint topics have been prompted already |
| `FINAL_REPORTED` | `Set[str]` | Sessions that have already generated a final report |

All state is in-memory. It is lost when the server restarts.

---

## API Schema

### Request

```json
{
  "sessionId": "string",
  "message": {
    "sender": "scammer",
    "text": "string",
    "timestamp": "ISO string or unix ms"
  },
  "conversationHistory": [
    { "sender": "string", "text": "string", "timestamp": "..." }
  ],
  "metadata": {}
}
```

Field aliases accepted:
- `sessionId` → also `sessionld` or `session_id`
- `conversationHistory` → also `conversation_history`
- `metadata` is optional

Flat `sender` and `text` at root level are also accepted as fallback.

### Normal Response

```json
{
  "status": "success",
  "reply": "string",
  "finalCallback": null,
  "finalOutput": null
}
```

### Finalization Response

```json
{
  "status": "success",
  "reply": "string",
  "finalCallback": {
    "sessionId": "string",
    "status": "completed",
    "scamDetected": true,
    "totalMessagesExchanged": 18,
    "engagementDurationSeconds": 240,
    "scamType": "bank_fraud | upi_fraud | phishing | job_scam | investment_scam | lottery_scam | kyc_scam | utility_scam | unknown",
    "confidenceLevel": 0.92,
    "extractedIntelligence": {
      "phoneNumbers": [],
      "bankAccounts": [],
      "upiIds": [],
      "phishingLinks": [],
      "emailAddresses": [],
      "caseIds": [],
      "policyNumbers": [],
      "orderNumbers": [],
      "referenceIds": []
    },
    "engagementMetrics": {
      "totalMessagesExchanged": 18,
      "engagementDurationSeconds": 240
    },
    "agentNotes": "Session completed. scamType=bank_fraud."
  },
  "finalOutput": { "...same object..." }
}
```

`finalCallback` and `finalOutput` carry the same data. `finalOutput` exists for backward compatibility.

### Error Responses

| Code | Cause |
|---|---|
| 403 | Missing or wrong `x-api-key` header |
| 422 | Malformed request body (Pydantic validation failure) |

---

## Dependency Graph (Import Order)

```
config.py        ← no internal deps (leaf)
schemas.py       ← no internal deps (leaf)
session_state.py ← no internal deps (leaf)
utils/text.py    ← no internal deps (leaf)

services/scoring.py      ← utils/text
services/extraction.py   ← utils/text, schemas
services/reply_generation.py ← config, schemas, session_state, utils/text, services/scoring
services/reporting.py    ← config, schemas, session_state, services/extraction

routes/detect.py  ← config, schemas, session_state, services/scoring,
                     services/extraction, services/reply_generation, services/reporting

main.py           ← config, routes/detect
```

The graph is strictly acyclic. Leaf modules have no internal imports.

---

## Known Architectural Risks

1. **Session memory growth** — No TTL. `SESSION_*` dicts grow forever.
2. **Hardcoded `scamDetected: true`** — The final report always flags a scam regardless of actual score.
3. **Engagement duration inflation** — Artificially padded to 181+ seconds when message count ≥ 16.
4. **Single Groq key, no retry** — Any Groq API failure falls back to a static reply with no logging.
5. **No CORS** — Browser clients are blocked.
6. **No input sanitisation** — Raw user text goes directly to regex and the LLM prompt.
