# ROADMAP

This document outlines planned development in phases. Items are ordered by dependency and value. Nothing here is committed — this is a planning reference.

---

## Phase 1: Stability and Completeness (Next Steps)

The API pipeline works. Phase 1 fixes the gaps that would prevent this from being used reliably even in a demo context.

### 1.1 Session cleanup and memory management

- Add a TTL (time-to-live) for sessions. Sessions inactive for more than N minutes should be removed from memory.
- Prevents the in-memory session dicts from growing without bound.
- Requires changes to `src/session_state.py` and a background cleanup task.

### 1.2 Health check endpoint

- Add `GET /health` returning `{ "status": "ok" }`.
- Required by most deployment platforms and load balancers.
- One route in `src/routes/`, registered in `src/main.py`.

### 1.3 CORS configuration

- Add `fastapi.middleware.cors.CORSMiddleware` to allow browser-based clients.
- Required before any frontend can talk to the API.
- Configured in `src/main.py`.

### 1.4 Rate limiting

- Add per-IP or per-key request rate limiting.
- Prevents API abuse.
- Can use `slowapi` (a FastAPI-compatible rate limiter).

### 1.5 Structured logging

- Replace `print()` with Python's `logging` module.
- Include log levels (DEBUG, INFO, WARNING, ERROR).
- Include session ID in each log line.
- Write to stdout in structured JSON format for easy parsing.

---

## Phase 2: Persistence

Right now all data is lost on restart. Phase 2 adds storage.

### 2.1 SQLite database (initial)

- Store sessions, extracted intelligence per session, and final reports in a local SQLite database.
- Enough for a demo or research context without infrastructure complexity.
- Schema: `sessions` table, `extracted_intel` table, `reports` table.

### 2.2 Retrieval endpoints

- `GET /sessions` — list all sessions
- `GET /sessions/{sessionId}` — get session details and extracted intel
- `GET /reports` — list all generated reports
- `GET /reports/{sessionId}` — get the final report for a session

### 2.3 PostgreSQL migration (production target)

- Replace SQLite with PostgreSQL for multi-instance deployment.
- Use SQLAlchemy or a lightweight async ORM.

---

## Phase 3: Frontend / Dashboard

The current system is API-only. Phase 3 adds a visual interface.

### 3.1 Core dashboard (three panels)

- **Chat view** — conversation replay, scammer messages on one side, honeypot replies on the other
- **Intelligence panel** — live-updating list of extracted data as the conversation progresses
- **Report card** — final report displayed when a session finalises

### 3.2 Session list

- Browse all sessions, see status (active / finalized), filter by scam type

### 3.3 Technology choice

- A simple HTML/JS frontend served from the FastAPI app is the simplest approach.
- React or Next.js for a richer interface if needed.

---

## Phase 4: Security Hardening

Before any public-facing deployment.

### 4.1 Per-user API keys or JWT authentication

- Replace the single shared `API_SECRET_KEY` with per-client authentication.
- Allows audit trails per caller.

### 4.2 Input sanitisation

- Validate and sanitise the `text` field before it reaches regex and the LLM prompt.
- Prevents prompt injection and overly large inputs.

### 4.3 Fix hardcoded values

- `scamDetected` is currently always `True`. Compute it from the actual scam score.
- Engagement duration inflation is artificial. Use real duration only.

### 4.4 Retry logic for Groq API

- Retry with exponential backoff on transient Groq failures.
- Log failures with enough context to diagnose them later.

---

## Phase 5: Research and Evaluation

Needed if this becomes a research paper submission.

### 5.1 Dataset collection

- Collect or curate a dataset of real scam conversation examples (with appropriate ethics review).
- Use it for evaluation instead of synthetic test scenarios.

### 5.2 Baseline comparison

- Implement a simple template-based honeypot as a baseline.
- Compare extraction quality and engagement duration between the LLM-based system and the baseline.

### 5.3 ML-based entity extraction

- Supplement regex with a NER model (e.g., a fine-tuned BERT or spaCy model) for more robust extraction.
- Especially useful for extracting names, locations, and unusual identifier formats.

### 5.4 Multi-language support

- Extend prompt and extraction to handle Hindi and other Indian languages.
- Replace India-specific phone regex with a more general pattern.

### 5.5 Ethics and responsible disclosure

- Define a data handling policy for extracted intelligence.
- Document responsible use guidelines.
- Consider IRB or institutional ethics review if using real scammer data.

---

## Phase 6: Product / Deployment

For a production or commercial direction.

### 6.1 Docker and deployment

- Add a `Dockerfile` and `docker-compose.yml`.
- Document deployment to Render, Fly.io, or a VPS.

### 6.2 CI/CD

- GitHub Actions: lint, test, build on every push.

### 6.3 Monitoring and alerting

- Basic metrics: requests per minute, LLM call latency, error rates.
- Alert on elevated error rate or Groq API failures.

### 6.4 Webhook delivery

- Push `finalCallback` to a configurable URL when a session finalises.
- Useful for integrating with existing security operations workflows.

### 6.5 Multi-channel support

- Extend beyond REST API to receive messages from SMS gateways, WhatsApp Business API, or email.
