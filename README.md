<p align="center">
  <img src="https://img.shields.io/badge/Project-NIRIKSHA.ai-blueviolet?style=for-the-badge&logo=shield" alt="NIRIKSHA.ai"/>
  <img src="https://img.shields.io/badge/India%20AI%20Impact-Buildathon%202026-orange?style=for-the-badge" alt="Buildathon 2026"/>
</p>

<h1 align="center">🛡️Agentic AI Honeypot for Scam Detection, Engagement, and Intelligence Extraction</h1>
<h3 align="center">Agentic Honeypot for Scam Detection, Engagement, and Intelligence Extraction</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Groq-Llama%203.3%2070B-FF6F00?style=flat-square&logo=meta&logoColor=white"/>
  <img src="https://img.shields.io/badge/Status-Research%20Prototype-yellow?style=flat-square"/>
</p>

---

## Overview

NIRIKSHA.ai is an AI-powered honeypot backend. When a scammer sends a message, the system pretends to be a confused but cooperative person, holds the conversation open across multiple turns, and silently extracts identifying information (phone numbers, UPI IDs, bank accounts, phishing links, email addresses, reference IDs). After roughly 10 turns, it produces a structured intelligence report including a scam-type classification.

The project is a Python/FastAPI REST API. It has no frontend and no persistent database. All session state is in-memory. It was built for the India AI Impact Buildathon 2026 and is accurately classified as a **research prototype**.

---

## Problem Statement

Traditional anti-scam tools block fraudsters immediately. While this stops a single attempt, it reveals nothing about the scammer — no phone number, no UPI, no infrastructure, no pattern. Scammers simply move on. NIRIKSHA.ai takes a different approach: keep the scammer talking long enough to extract intelligence, then report it.

---

## Core Idea

An LLM agent mimics a cautious, slightly confused person. It engages the scammer across multiple conversation turns, asking for identifying details (reference numbers, email, phone, UPI, bank account, verification link) without ever revealing that it is an AI or that it has recognised the scam. All of this happens behind a single REST endpoint.

---

## Key Workflow

```
POST /api/detect (with sessionId, message, conversationHistory)
  → API key check
  → Session init or resume (in-memory)
  → Scam signal scoring (regex)
  → Intelligence extraction (regex, full conversation)
  → Choose next hint topic (missing intel category)
  → Generate reply (Groq / Llama 3.3 70B)
  → Sanitize reply (banned words, 1-question limit, 200-char cap)
  → Enforce rubric guardrails on designated turns
  → Check finalization (turn ≥ 10, or turn ≥ 8 with enough intel)
      → If finalizing: classify scam type (LLM), build report
  → Return { status, reply, finalCallback, finalOutput }
```

---

## What Is Working Right Now

| Capability | Status |
|---|---|
| `POST /api/detect` endpoint | Working |
| Multi-turn session management (in-memory) | Working |
| LLM reply generation (Groq, Llama 3.3 70B) | Working |
| Scam signal scoring (regex-based) | Working |
| Intelligence extraction (9 field types) | Working |
| Reply sanitization and guardrails | Working |
| Final report generation | Working |
| LLM scam type classification | Working |
| API key authentication | Working |
| Integration test harness (5 scenarios) | Working |
| Modular codebase (split from single file) | Done |

**Test result (local run, April 2026):** 96.65 / 100 across 5 weighted scam scenarios.

---

## Limitations

- No database. All session data is lost on server restart.
- No frontend or dashboard. Interaction is API-only.
- `scamDetected` is hardcoded to `True` in every final report.
- Engagement duration is artificially inflated for sessions with 16+ messages.
- Session dicts grow unbounded (no TTL or cleanup).
- Single shared API key (no per-user authentication).
- No rate limiting. Endpoint can be freely abused.
- No CORS configuration (browser-based clients will be blocked).
- Phone number extraction is India-specific (+91, 10-digit starting with 6–9).
- Extraction is regex-only; no ML-based entity recognition.
- No structured logging. Logs are `print()` statements to stdout only.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Framework | FastAPI |
| LLM Provider | Groq API |
| LLM Model | Meta Llama 3.3 70B (`llama-3.3-70b-versatile`) |
| Validation | Pydantic v2 |
| Server | uvicorn |
| Dependencies | fastapi, uvicorn, groq, pydantic, requests, python-dotenv |

---

## Repository Structure

```
NIRIKSHA.ai/
├── src/
│   ├── main.py                  # App entry point (slim): FastAPI app, router wiring, uvicorn runner
│   ├── config.py                # Env vars, Groq client, API key, delay constants, log_chat()
│   ├── schemas.py               # Pydantic models: MessageItem, IncomingRequest, AgentResponse
│   ├── session_state.py         # In-memory session dicts (6 global state objects)
│   ├── utils/
│   │   └── text.py              # Regex patterns, word lists, norm(), _clean_url(), _normalize_phone()
│   ├── services/
│   │   ├── scoring.py           # calculate_scam_score(), looks_like_payment_targeted()
│   │   ├── extraction.py        # extract_intelligence(), high_value_count()
│   │   ├── reply_generation.py  # _llm_generate_reply(), _sanitize_reply(), _next_hint(), _enforce_minimums()
│   │   └── reporting.py         # infer_scam_type(), build_final_output()
│   ├── routes/
│   │   └── detect.py            # detect_scam() route handler on APIRouter
│   └── tests/
│       └── test_chat.py         # Integration test: 5 weighted scam scenarios
├── docs/
│   ├── OVERVIEW.md              # Project purpose, use cases, positioning
│   ├── ARCHITECTURE.md          # System flow, modules, data flow
│   ├── CURRENT_STATUS.md        # What works, what is partial, what is missing
│   ├── FEATURE_MATRIX.md        # Complete feature table with status and file references
│   ├── ROADMAP.md               # Phased future development plan
│   └── PROJECT_AUDIT.md         # Detailed technical audit of the codebase
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── .gitignore
```

---

## How to Run Locally

### Prerequisites

- Python 3.10 or higher
- A free Groq API key from [console.groq.com/keys](https://console.groq.com/keys)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/ABHI99RAJPUT/NIRIKSHA.ai.git
cd NIRIKSHA.ai

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
# Copy .env.example to .env and fill in the two required values:
#   GROQ_API_KEY=your_groq_api_key_here
#   API_SECRET_KEY=any_password_you_choose

# 5. Start the server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

> **Note on `API_SECRET_KEY`:** This is a password you choose yourself. It is not from Groq or any external service. Pick any string (e.g. `my-secret-123`) and use the same value in your `.env` and in `test_chat.py`.

### Run the Integration Tests

The server must be running before you run the tests.

```bash
# In src/tests/test_chat.py, set API_KEY to match your API_SECRET_KEY
python src/tests/test_chat.py
```

---

## API Overview

**Endpoint:** `POST /api/detect`

**Required headers:**

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `x-api-key` | Must match `API_SECRET_KEY` in your `.env` |

**Minimal request:**

```json
{
  "sessionId": "any-unique-string",
  "message": {
    "sender": "scammer",
    "text": "Your account is blocked. Share OTP now.",
    "timestamp": "2026-01-01T10:00:00Z"
  },
  "conversationHistory": []
}
```

**Normal response (turns 1–9):**

```json
{
  "status": "success",
  "reply": "Oh no, that sounds serious. What is the reference number for this?",
  "finalCallback": null,
  "finalOutput": null
}
```

**Response on finalization (turn 10+):**

`finalCallback` and `finalOutput` contain the full intelligence report including extracted phone numbers, UPI IDs, bank accounts, phishing links, emails, reference IDs, scam type, and confidence level.

**Errors:**

| Code | Cause |
|---|---|
| 403 | Missing or incorrect `x-api-key` header |
| 422 | Malformed request body |

Full API and schema details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Authenticates with the Groq LLM service. Server will crash on startup if missing. |
| `API_SECRET_KEY` | Yes | `""` (all requests fail with 403) | A password you set for your own API endpoint. |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | LLM model to use |
| `MIN_HUMAN_DELAY_S` | No | `0.10` | Minimum simulated reply delay (seconds) |
| `MAX_HUMAN_DELAY_S` | No | `0.28` | Maximum simulated reply delay (seconds) |
| `PORT` | No | `8000` | Server port |

---

## Current Project Status

**Classification: Research Prototype / Hackathon Submission**

The API pipeline is complete and tested. The codebase has been refactored from a single 626-line file into a modular structure. There is no persistent storage, no frontend, and no deployment infrastructure. The system is suitable for local demonstration and academic evaluation.

See [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) for a detailed breakdown.

---

## Planned Next Steps

1. Add a web-based dashboard (conversation view, extracted data panel, final report card)
2. Add persistent storage (SQLite to start) so data survives server restarts
3. Add session TTL and cleanup to prevent memory growth
4. Add rate limiting middleware
5. Add CORS configuration for browser-based access
6. Add a health check endpoint (`GET /health`)
7. Write proper unit tests with pytest
8. Add Docker support
9. Add structured logging

See [docs/ROADMAP.md](docs/ROADMAP.md) for phased planning.

---

## Research and Academic Relevance

The core idea of using an LLM-driven agent as a honeypot for scam intelligence extraction is novel. The key technical contribution is the agentic conversation loop: a persona-driven LLM that maintains a believable identity across turns while strategically eliciting identifying information from a scammer, without the scammer realising it.

For a research paper, this would need: a dataset of real or realistic scam conversations, comparison with baseline approaches, independent evaluation metrics, and ethical review. For a college mini-project or hackathon submission, the current implementation is complete and demonstrable.

See [docs/OVERVIEW.md](docs/OVERVIEW.md) for positioning details.

---

## Documentation Index

| Document | Purpose |
|---|---|
| [docs/OVERVIEW.md](docs/OVERVIEW.md) | Project purpose, use cases, academic and product positioning |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System flow, module breakdown, API schemas, data flow |
| [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md) | What is working, partial, and missing right now |
| [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md) | Complete feature table with status and file references |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phased future development plan |
| [docs/PROJECT_AUDIT.md](docs/PROJECT_AUDIT.md) | Detailed technical audit of the codebase |

---

## Team

<table>
  <tr>
    <td align="center">
      <b>Vanshaj Garg</b><br/>
      <a href="mailto:official.vanshaj.garg@gmail.com">official.vanshaj.garg@gmail.com</a><br/>
      <a href="https://www.linkedin.com/in/vanshajgargg">LinkedIn</a>
    </td>
    <td align="center">
      <b>Abhishek Rajput</b><br/>
      <a href="mailto:rajputabhishek512@gmail.com">rajputabhishek512@gmail.com</a><br/>
      <a href="https://www.linkedin.com/in/abhi-99-rajput/">LinkedIn</a>
    </td>
    <td align="center">
      <b>Abhay Raj Yadav</b><br/>
      <a href="mailto:19abhay26@gmail.com">19abhay26@gmail.com</a><br/>
      <a href="https://www.linkedin.com/in/contactabhayraj">LinkedIn</a>
    </td>
  </tr>
</table>

---

## License

Built for the **India AI Impact Buildathon 2026** organised by HCL GUVI. No open-source license is currently applied to this repository.
