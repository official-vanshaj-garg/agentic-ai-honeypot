# DATABASE INTEGRATION PLAN

**Planning date:** April 2026
**Target database:** SQLite (local file)
**Target ORM:** SQLModel (Pydantic + SQLAlchemy hybrid, already compatible with the project)
**Scope:** First version. Simple. No PostgreSQL, no Redis, no Docker, no Alembic.

---

## 1. CURRENT DATA FLOW

This section traces exactly where session data, extracted indicators, and reports are created and updated in the existing code.

### 1.1 Session creation and updates

**File:** `src/routes/detect.py` (lines 42-48)

When a request arrives, the handler checks whether `session_id` already exists in `SESSION_START_TIMES`. If not, it initialises all six in-memory dicts:

```python
session_id = payload.session_id or str(uuid.uuid4())
if session_id not in SESSION_START_TIMES:
    SESSION_START_TIMES[session_id] = time.time()        # float: unix timestamp
    SESSION_TURN_COUNT[session_id] = 0                   # int
    SESSION_SCAM_SCORE[session_id] = 0                   # int
    SESSION_COUNTS[session_id] = {"q": 0, "inv": 0, "rf": 0, "eli": 0}  # dict
    SESSION_ASKED[session_id] = set()                    # set of strings
```

On every turn (line 51):
```python
SESSION_TURN_COUNT[session_id] += 1
```

After scoring (line 59):
```python
SESSION_SCAM_SCORE[session_id] += calculate_scam_score(text)
```

After reply generation (lines 83-85):
```python
feats = _count_features(reply)
for k in ("q", "inv", "rf", "eli"):
    SESSION_COUNTS[session_id][k] += feats.get(k, 0)
```

**File:** `src/session_state.py` — six module-level dicts. These are the objects being mutated above.

**File:** `src/services/reply_generation.py` (line 87) — `_next_hint()` mutates `SESSION_ASKED`:
```python
SESSION_ASKED.setdefault(session_id, set()).add(key)
```

### 1.2 Extracted indicators

**File:** `src/services/extraction.py`, function `extract_intelligence()` (lines 50-102)

Called at two points:
1. `src/routes/detect.py` line 60 — "preview" extraction on every turn (result used for hint selection and finalization check, not currently saved anywhere)
2. `src/services/reporting.py` line 64 — called again from `build_final_output()` at finalization (result embedded in the final report dict)

The function returns a dict with nine keys:
```python
{
    "phoneNumbers": [...],
    "bankAccounts": [...],
    "upiIds": [...],
    "phishingLinks": [...],
    "emailAddresses": [...],
    "caseIds": [...],
    "policyNumbers": [...],
    "orderNumbers": [...],
    "referenceIds": [...]
}
```

Each value is `List[str]`, already sorted and deduplicated.

**Normalisation already happening:**
- Phones → `_normalize_phone()` in `src/utils/text.py` (lines 42-50): strips whitespace/dashes, prepends `+91` for 10-digit Indian numbers
- URLs → `_clean_url()` in `src/utils/text.py` (lines 39-40): strips trailing punctuation
- UPI IDs → email overlap filtering in `src/services/extraction.py` (lines 60-72)
- Bank accounts → phone overlap and epoch timestamp filtering (`src/services/extraction.py` lines 74-87)
- Reference IDs → uppercase, dash-normalised (`src/services/extraction.py` lines 15-32)
- Emails → no normalisation (raw regex match)

### 1.3 Report generation

**File:** `src/services/reporting.py`, function `build_final_output()` (lines 63-98)

Called from `src/routes/detect.py` line 99, only when the finalization condition is met. The function:
1. Calls `extract_intelligence()` again for the final extraction snapshot
2. Reads `SESSION_START_TIMES[session_id]` for duration calculation
3. Calls `infer_scam_type()` (a second Groq API call) for classification
4. Assembles a dict with: `sessionId`, `status`, `scamDetected`, `totalMessagesExchanged`, `engagementDurationSeconds`, `scamType`, `confidenceLevel`, `extractedIntelligence`, `engagementMetrics`, `agentNotes`
5. Prints it to stdout, returns it

The returned dict becomes both `finalCallback` and `finalOutput` in the API response.

### 1.4 Summary: where DB hooks will eventually be needed

| Hook point | File | Line(s) | What to write |
|---|---|---|---|
| Session creation | `src/routes/detect.py` | 42-48 | Insert new `Session` row |
| Turn increment and incoming message | `src/routes/detect.py` | 51-53 | Insert `Message` row (sender=scammer) |
| Scam score update | `src/routes/detect.py` | 59 | Update `Session.scam_score` |
| Extracted indicators (per-turn) | `src/routes/detect.py` | 60 | Upsert `Indicator` + `SessionIndicator` rows |
| Reply saved | `src/routes/detect.py` | 89 | Insert `Message` row (sender=honeypot) |
| Session finalised | `src/routes/detect.py` | 98-99 | Insert `Report` row; update `Session.status` |

---

## 2. RECOMMENDED DATABASE APPROACH

### Why SQLite

- The project is a single-process Python application running locally.
- There is no multi-instance deployment, no containerisation, and no cloud database requirement.
- SQLite requires zero infrastructure. The database is a single file alongside the code.
- SQLite handles the expected load (local testing, demos, academic evaluation) with no performance concerns.
- SQLite is already bundled with Python (the `sqlite3` module is in the standard library).

### Why SQLModel

- SQLModel is built on SQLAlchemy and Pydantic. The project already uses Pydantic v2 for its request/response schemas.
- SQLModel tables are defined as Python classes that look and feel like Pydantic models, so the pattern is already familiar in this codebase.
- It avoids the complexity of raw SQL while also avoiding the full weight of a Django-style ORM.
- SQLModel supports SQLite out of the box with `sqlite:///filename.db`.

### Why keep it simple

- The first goal is to add persistence without changing any existing behavior.
- No Alembic (migration tool) in V1 because the schema will be small and stable. If the schema changes later, Alembic can be added then.
- No async engine. The current code already uses `asyncio.to_thread()` for the Groq API call, so DB writes can follow the same pattern if needed. But SQLite with synchronous writes from an async FastAPI handler is fine for single-user local use.

---

## 3. PROPOSED SCHEMA

### 3.1 Session

**Purpose:** One row per conversation session. Maps directly to what is currently spread across six in-memory dicts.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `str` (PK) | Yes | The `session_id` from the API. Not auto-generated. |
| `started_at` | `float` | Yes | Unix timestamp. Currently `SESSION_START_TIMES[sid]`. |
| `turn_count` | `int` | Yes | Default 0. Currently `SESSION_TURN_COUNT[sid]`. |
| `scam_score` | `int` | Yes | Default 0. Currently `SESSION_SCAM_SCORE[sid]`. |
| `rubric_q` | `int` | Yes | Default 0. `SESSION_COUNTS[sid]["q"]`. |
| `rubric_inv` | `int` | Yes | Default 0. `SESSION_COUNTS[sid]["inv"]`. |
| `rubric_rf` | `int` | Yes | Default 0. `SESSION_COUNTS[sid]["rf"]`. |
| `rubric_eli` | `int` | Yes | Default 0. `SESSION_COUNTS[sid]["eli"]`. |
| `asked_hints` | `str` | Yes | Default `""`. Comma-separated set. Currently `SESSION_ASKED[sid]`. |
| `status` | `str` | Yes | `"active"` or `"completed"`. Currently inferred from `FINAL_REPORTED`. |
| `created_at` | `datetime` | Yes | Row creation time (for queries). |
| `updated_at` | `datetime` | Yes | Updated on every turn. |

**Relationships:**
- One Session → many Messages
- One Session → many SessionIndicators
- One Session → zero or one Report

**Design decisions:**
- `asked_hints` is stored as a comma-separated string (e.g. `"reference,link,email"`) rather than a separate table, because the set is small (max ~6 items), and a join table would add complexity for no practical benefit in V1.
- The four `rubric_*` fields are stored flat rather than as JSON, so they can be queried and compared directly.

### 3.2 Message

**Purpose:** Store every message in a session (both scammer messages and honeypot replies).

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `int` (PK, auto) | Yes | Auto-incrementing. |
| `session_id` | `str` (FK → Session) | Yes | |
| `sender` | `str` | Yes | `"scammer"` or `"honeypot"` |
| `text` | `str` | Yes | The message content. |
| `turn_number` | `int` | Yes | Which turn this message belongs to. |
| `timestamp` | `datetime` | Yes | When the message was received/generated. |

**Relationships:**
- Many Messages → one Session

**Notes:**
- Both the incoming scammer message and the outgoing honeypot reply for a given turn share the same `turn_number`. The `sender` field distinguishes them.
- The original `timestamp` from the incoming request payload (if present) is not used for this field. This field records the actual server time when the message was processed.

### 3.3 Indicator

**Purpose:** A global table of all unique indicators ever seen across all sessions. This is the foundation for repeated-threat detection.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `int` (PK, auto) | Yes | |
| `indicator_type` | `str` | Yes | One of: `phone`, `bank_account`, `upi`, `phishing_link`, `email`, `reference_id` |
| `value` | `str` | Yes | The normalised indicator value. |
| `first_seen_at` | `datetime` | Yes | When this indicator was first encountered. |
| `last_seen_at` | `datetime` | Yes | Updated every time this indicator appears again. |
| `hit_count` | `int` | Yes | Default 1. Incremented each time this indicator is seen in a new session. |

**Unique constraint:** `(indicator_type, value)` — each normalised value appears exactly once per type.

**Relationships:**
- One Indicator → many SessionIndicators

**Notes:**
- `value` is always stored in normalised form (see Section 4).
- `hit_count` counts distinct sessions, not distinct messages. If the same phone number appears in 3 messages within one session, that is still `hit_count = 1` for that session.

### 3.4 SessionIndicator

**Purpose:** Link table between sessions and indicators. Records which indicators were extracted from which session.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `int` (PK, auto) | Yes | |
| `session_id` | `str` (FK → Session) | Yes | |
| `indicator_id` | `int` (FK → Indicator) | Yes | |
| `extracted_at` | `datetime` | Yes | When this link was first created. |

**Unique constraint:** `(session_id, indicator_id)` — each indicator appears at most once per session.

**Relationships:**
- Many SessionIndicators → one Session
- Many SessionIndicators → one Indicator

**Notes:**
- This is the table that enables the query "which sessions share a common indicator?" and "which indicators have been seen across multiple sessions?"

### 3.5 Report

**Purpose:** Store the final report generated when a session is completed. One report per session.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `int` (PK, auto) | Yes | |
| `session_id` | `str` (FK → Session, unique) | Yes | One report per session. |
| `scam_type` | `str` | Yes | From `infer_scam_type()`. |
| `confidence` | `float` | Yes | 0.0 to 1.0. |
| `total_messages` | `int` | Yes | `totalMessagesExchanged` from the report. |
| `duration_seconds` | `int` | Yes | `engagementDurationSeconds` from the report. |
| `full_report_json` | `str` | Yes | The complete `build_final_output()` dict, serialised as JSON. |
| `created_at` | `datetime` | Yes | When the report was generated. |

**Relationships:**
- One Report → one Session

**Design decision:**
- The full report dict is stored as a JSON string (`full_report_json`) so that the complete API response can be reconstructed exactly. The key fields (`scam_type`, `confidence`, `total_messages`, `duration_seconds`) are duplicated as queryable columns.

### Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│   Session    │──1:N──│     Message      │       │    Report    │
│              │       └──────────────────┘       │              │
│   id (PK)    │──1:1──────────────────────────── │  session_id  │
│              │       ┌──────────────────┐       └──────────────┘
│              │──1:N──│SessionIndicator  │
└──────────────┘       │  session_id (FK) │
                       │  indicator_id(FK)│
                       └────────┬─────────┘
                                │ N:1
                       ┌────────┴─────────┐
                       │   Indicator      │
                       │   id (PK)        │
                       │   (type, value)  │
                       │   UNIQUE         │
                       └──────────────────┘
```

---

## 4. NORMALISATION STRATEGY

Before storing an indicator in the `Indicator` table, normalise the value. The goal is that the same real-world entity always maps to the same `(indicator_type, value)` pair.

### Phone numbers

Normalisation is already done by `_normalize_phone()` in `src/utils/text.py`:
- Strip whitespace and dashes
- Prepend `+91` for 10-digit numbers starting with 6-9
- Result: `+91XXXXXXXXXX`

**For DB storage:** Use the output of `_normalize_phone()` as-is. Example: `+919876543210`.

### UPI IDs

Currently stored as raw regex matches, filtered to exclude emails.

**For DB storage:** Lowercase the full UPI ID. Example: `scammer@fakeupi` → `scammer@fakeupi`.

### Bank account numbers

Currently stored as raw digit strings (9-18 digits), after phone and epoch overlap filtering.

**For DB storage:** Store as-is (raw digit string). No further normalisation needed. Example: `1234567890123456`.

### Email addresses

Currently stored as raw regex matches.

**For DB storage:** Lowercase the entire email. Example: `Support@FakeBank.com` → `support@fakebank.com`.

### Phishing links

Currently cleaned by `_clean_url()` which strips trailing punctuation.

**For DB storage:** Lowercase the URL. Strip trailing slashes. Example: `http://Fake-Site.com/page/` → `http://fake-site.com/page`.

### Reference IDs

Currently normalised by `_extract_reference_ids()`: uppercased, whitespace/colons replaced with dashes.

**For DB storage:** Use the output of `_extract_reference_ids()` as-is (already uppercase and dash-normalised). Example: `CASE-12345`.

### Mapping extraction output keys to `indicator_type`

| Extraction key | `indicator_type` value |
|---|---|
| `phoneNumbers` | `phone` |
| `bankAccounts` | `bank_account` |
| `upiIds` | `upi` |
| `phishingLinks` | `phishing_link` |
| `emailAddresses` | `email` |
| `referenceIds` | `reference_id` |

**Note:** `caseIds`, `policyNumbers`, and `orderNumbers` are subsets of `referenceIds` (they are derived from the same extraction by `_split_ids()`). Only `referenceIds` values are stored in the `Indicator` table. The subcategorisation can be derived from the value prefix at query time.

---

## 5. REPEATED THREAT DETECTION PLAN

### What "repeated threat" means

A repeated threat is an indicator (phone number, UPI ID, bank account, etc.) that appears across more than one session. This means the same scammer infrastructure is being reused across multiple scam attempts.

### How to detect it

The `Indicator` table has three fields that enable this:

| Field | Purpose |
|---|---|
| `first_seen_at` | When this indicator was first extracted from any session |
| `last_seen_at` | When this indicator was most recently seen |
| `hit_count` | How many distinct sessions have produced this indicator |

### Write flow

When `extract_intelligence()` returns a set of indicators for a session:

1. For each indicator `(type, normalised_value)`:
   a. Check if it already exists in `Indicator` table.
   b. If **not found**: INSERT with `hit_count=1`, `first_seen_at=now`, `last_seen_at=now`.
   c. If **found**: UPDATE `last_seen_at=now`, `hit_count += 1`.
   d. Create a `SessionIndicator` row linking this session to this indicator (if not already linked).

### Read flow (for future use)

Queries that become possible after this is implemented:

```sql
-- Find all indicators seen in more than one session (repeated threats)
SELECT indicator_type, value, hit_count, first_seen_at, last_seen_at
FROM indicator
WHERE hit_count > 1
ORDER BY hit_count DESC;

-- Find all sessions that share a specific phone number
SELECT si.session_id, s.started_at, s.status
FROM session_indicator si
JOIN session s ON si.session_id = s.id
JOIN indicator i ON si.indicator_id = i.id
WHERE i.indicator_type = 'phone' AND i.value = '+919876543210';

-- Find all indicators from a specific session
SELECT i.indicator_type, i.value, i.hit_count
FROM session_indicator si
JOIN indicator i ON si.indicator_id = i.id
WHERE si.session_id = 'some-session-id';
```

### Future enrichment

Once repeated threats are detectable, the system could:
- Include a `"repeated": true` flag in the final report for known indicators
- Adjust the scam confidence score upward for sessions containing repeated indicators
- Surface a "known infrastructure" section in a future dashboard

These are future features. The DB schema supports them without modification.

---

## 6. MINIMAL FILE CHANGE PLAN

### New files to create

| File | Purpose |
|---|---|
| `src/db.py` | SQLModel engine, `create_db()`, `get_session()` dependency. ~30-40 lines. |
| `src/models.py` | SQLModel table classes: `Session`, `Message`, `Indicator`, `SessionIndicator`, `Report`. ~80-100 lines. |

### Existing files to modify

| File | What changes | Impact |
|---|---|---|
| `src/main.py` | Add `create_db()` call at startup (1 line). Add DB session dependency if using FastAPI Depends. | Very low. Entry point only. |
| `src/routes/detect.py` | Add 6 write points (see Section 7). Each is 3-8 lines of "write to DB after existing logic". No existing logic changes. | Medium complexity, but behaviour-preserving. |
| `src/session_state.py` | Keep unchanged in V1. The in-memory dicts continue to serve as the fast, in-process data layer. DB writes happen alongside, not instead of. | No change. |

### Files NOT changed

| File | Reason |
|---|---|
| `src/config.py` | No DB config needed. SQLite path can go in `src/db.py`. |
| `src/schemas.py` | API request/response schemas are unchanged. |
| `src/services/scoring.py` | Scoring logic unchanged. |
| `src/services/extraction.py` | Extraction logic unchanged. |
| `src/services/reply_generation.py` | Reply generation logic unchanged. |
| `src/services/reporting.py` | Report generation logic unchanged. |
| `src/utils/text.py` | Regex and normalisation unchanged. |
| `src/tests/test_chat.py` | Test harness hits the HTTP endpoint. It does not care about DB. |

### New dependency

Add to `requirements.txt`:
```
sqlmodel
```

This is the only new dependency. SQLModel brings SQLAlchemy with it. `sqlite3` is in the Python standard library.

---

## 7. SAFE WRITE POINTS

These are the exact locations in the current request flow where DB writes should be inserted. Each write happens **after** the existing logic, so it cannot affect the return value or the in-memory state.

### 7.1 Session creation

**Where:** `src/routes/detect.py`, after line 48 (inside the `if session_id not in SESSION_START_TIMES` block).

**What:** Insert a `Session` row with `id=session_id`, `started_at=time.time()`, `status="active"`, `turn_count=0`, `scam_score=0`, rubric fields at 0, `asked_hints=""`.

**Risk:** None. Only runs on first turn. Does not affect anything downstream.

### 7.2 Incoming scammer message

**Where:** `src/routes/detect.py`, after line 53 (`log_chat("Scammer", text)`).

**What:** Insert a `Message` row with `session_id`, `sender="scammer"`, `text=text`, `turn_number=turn`.

**Risk:** None. Pure write. No read dependency.

### 7.3 Scam score and extracted indicators

**Where:** `src/routes/detect.py`, after line 60 (`preview = extract_intelligence(...)`).

**What:**
1. Update `Session.scam_score` and `Session.turn_count`.
2. For each indicator in `preview`: upsert into the `Indicator` table, create `SessionIndicator` link.

**Risk:** Low. The `preview` dict is already computed. We are adding a write after the existing read. The existing code does not depend on the write result.

### 7.4 Honeypot reply message

**Where:** `src/routes/detect.py`, after line 89 (`log_chat("Honeypot", reply)`).

**What:** Insert a `Message` row with `session_id`, `sender="honeypot"`, `text=reply`, `turn_number=turn`.

Also update `Session` rubric fields (`rubric_q`, `rubric_inv`, `rubric_rf`, `rubric_eli`) and `asked_hints` to match the in-memory state.

**Risk:** None. Pure write.

### 7.5 Final report

**Where:** `src/routes/detect.py`, after line 99 (`final_obj = build_final_output(...)`).

**What:**
1. Insert a `Report` row with the report data and full JSON.
2. Update `Session.status` to `"completed"`.

**Risk:** None. The return value (`final_obj`) is already computed. The DB write does not affect it.

### Write point summary

```python
# Pseudocode annotation of detect_scam() with write points:

async def detect_scam(...):
    # ... auth check ...
    # ... parse message ...
    
    # Session init
    if session_id not in SESSION_START_TIMES:
        # ... existing dict init ...
        # ► DB WRITE 1: Insert Session row
    
    SESSION_TURN_COUNT[session_id] += 1
    log_chat("Scammer", text)
    # ► DB WRITE 2: Insert Message(sender="scammer")
    
    SESSION_SCAM_SCORE[session_id] += calculate_scam_score(text)
    preview = extract_intelligence(...)
    # ► DB WRITE 3: Update Session.scam_score, upsert Indicators + SessionIndicators
    
    hint = _next_hint(...)
    # ... LLM reply generation ...
    reply = _enforce_minimums(...)
    log_chat("Honeypot", reply)
    # ► DB WRITE 4: Insert Message(sender="honeypot"), update Session rubrics
    
    if turn >= 10 or (turn >= 8 and enough_intel):
        FINAL_REPORTED.add(session_id)
        final_obj = build_final_output(...)
        # ► DB WRITE 5: Insert Report row, update Session.status
    
    return AgentResponse(...)
```

---

## 8. RISKS

### 8.1 Performance impact on response time

SQLite writes are synchronous. Each turn would add ~5 write operations. On an SSD, each SQLite write takes <1ms, so the total overhead per turn is <5ms. The LLM call itself takes 500-2000ms. The DB overhead is negligible.

**Mitigation:** If this ever becomes a problem, wrap DB writes in `asyncio.to_thread()` (same pattern used for the Groq API call).

### 8.2 Import/startup order

`src/db.py` will call `SQLModel.metadata.create_all(engine)` to create tables. If this runs before models are imported, tables won't be created.

**Mitigation:** Import models explicitly in `src/db.py` or in `create_db()`. Standard SQLModel pattern.

### 8.3 Double extraction

`extract_intelligence()` is called twice for sessions that finalise: once at line 60 (preview) and again inside `build_final_output()` at reporting line 64. Both calls process the full conversation. The indicator upsert at Write Point 3 covers the preview call. The final report (Write Point 5) stores the full report JSON.

**Risk:** The final extraction at finalization might extract indicators that were not in the preview (because the conversation history is slightly different). This could mean some indicators appear in the report JSON but are not in the `Indicator` table.

**Mitigation:** At Write Point 5, also parse `final_obj["extractedIntelligence"]` and upsert any new indicators. This is a simple addition.

### 8.4 In-memory state and DB state could drift

If the process crashes between an in-memory update and the corresponding DB write, the DB would be behind.

**Risk:** Low. This is a local demo tool, not a banking system. If state drifts, the worst outcome is a missing row in the DB.

**Mitigation:** For V1, accept this risk. If needed later, wrap all writes in a SQLModel session transaction that commits once per turn.

### 8.5 DB file location and `.gitignore`

If the SQLite file is created in the project root, it could accidentally be committed.

**Mitigation:** Add `*.db` to `.gitignore`. Use a path like `data/niriksha.db` and add `data/` to `.gitignore`.

### 8.6 Circular imports

`src/models.py` will import SQLModel. `src/routes/detect.py` will import from `src/models.py` and `src/db.py`. This should not create circular dependencies because `models.py` and `db.py` are leaf modules that don't import from routes or services.

**Mitigation:** Standard Python module design. No action needed.

---

## 9. SAFE IMPLEMENTATION ORDER

Execute in this order. Each step is independently testable.

| Step | Task | Test after |
|---|---|---|
| **1** | Add `sqlmodel` to `requirements.txt`. Run `pip install -r requirements.txt`. | `python -c "import sqlmodel; print('ok')"` |
| **2** | Create `src/models.py` with all 5 SQLModel table classes. | `python -c "from src.models import Session, Message, Indicator, SessionIndicator, Report; print('ok')"` |
| **3** | Create `src/db.py` with `engine`, `create_db()`, `get_session()`. | `python -c "from src.db import create_db; create_db(); print('ok')"` — verify `.db` file is created with correct tables |
| **4** | Add `create_db()` call to `src/main.py` after app creation. | Start server with `uvicorn src.main:app`. Verify `.db` file is created. Verify API still returns 200. |
| **5** | Add Write Point 1 (session creation) to `src/routes/detect.py`. | Send a request. Check `Session` table has a row. |
| **6** | Add Write Points 2 and 4 (message saves) to `src/routes/detect.py`. | Send a request. Check `Message` table has 2 rows (scammer + honeypot). |
| **7** | Add Write Point 3 (indicator upserts) to `src/routes/detect.py`. | Send a request with scam content. Check `Indicator` and `SessionIndicator` tables. |
| **8** | Add Write Point 5 (report save) to `src/routes/detect.py`. | Run a 10-turn conversation. Check `Report` table has a row. Check `Session.status` is `"completed"`. |
| **9** | Add `*.db` and `data/` to `.gitignore`. | Verify DB file is not tracked by git. |
| **10** | Run `python src/tests/test_chat.py`. | All 5 scenarios pass. Scores are the same as before DB integration. |
| **11** | Inspect DB after full test run. | Verify: 5 sessions, messages for each, indicators populated, 5 reports. |

---

## 10. ACCEPTANCE CHECKLIST

After DB integration is complete, verify each of these:

### Application behaviour (unchanged)

- [ ] Server starts with `python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] `POST /api/detect` returns HTTP 200 with `{"status": "success", "reply": "...", "finalCallback": null}` on first turn
- [ ] `POST /api/detect` returns HTTP 403 with `{"detail": "Invalid API Key"}` without `x-api-key` header
- [ ] `POST /api/detect` returns HTTP 422 on malformed JSON
- [ ] `finalCallback` appears on turn 10 (or turn 8+ with enough intel)
- [ ] `finalCallback` contains all expected fields (same structure as before)
- [ ] Reply never contains banned words
- [ ] Reply contains at most one `?`
- [ ] Reply length is at most 200 characters

### Integration test

- [ ] Run `python src/tests/test_chat.py` — all 5 scenarios complete
- [ ] All 5 scenarios produce a `finalCallback` object
- [ ] Weighted score is comparable to pre-DB baseline (~96-99)

### Persistence

- [ ] After a single request, the `Session` table has one row
- [ ] After a single request, the `Message` table has two rows (one scammer, one honeypot)
- [ ] After a request with scam indicators, the `Indicator` table has rows
- [ ] After a 10-turn session, the `Report` table has one row with valid JSON
- [ ] After two sessions sharing the same phone number, `Indicator.hit_count = 2` for that phone
- [ ] `Session.status` is `"active"` for in-progress sessions and `"completed"` for finalised ones
- [ ] After server restart, DB data persists (re-query shows previous data)

### No side effects

- [ ] In-memory session state still works (multi-turn conversations complete correctly)
- [ ] Scoring behaviour is unchanged
- [ ] Extraction behaviour is unchanged
- [ ] Reply generation behaviour is unchanged
- [ ] Report structure is unchanged
- [ ] No new API endpoints (V1 adds persistence only, not retrieval)

### Housekeeping

- [ ] `*.db` is in `.gitignore`
- [ ] `sqlmodel` is in `requirements.txt`
- [ ] No other new dependencies added
- [ ] DB file is not committed to git