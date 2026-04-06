import uuid
import time
import random
import asyncio
from typing import Dict

from fastapi import APIRouter, HTTPException, Security

from src.config import API_SECRET_TOKEN, api_key_header, MIN_DELAY, MAX_DELAY, log_chat
from src.schemas import IncomingRequest, AgentResponse
from src.session_state import (
    SESSION_START_TIMES, SESSION_TURN_COUNT, SESSION_SCAM_SCORE,
    SESSION_COUNTS, SESSION_ASKED, FINAL_REPORTED,
)
from src.services.scoring import calculate_scam_score
from src.services.extraction import extract_intelligence, high_value_count
from src.services.reply_generation import (
    _sanitize_reply, _next_hint, _llm_generate_reply,
    _count_features, _enforce_minimums,
)
from src.services.reporting import build_final_output
from src.db import (
    db_create_session, db_save_message, db_update_session,
    db_upsert_indicators, db_save_report,
)

# ============================================================
# ENDPOINT
# ============================================================

router = APIRouter()


@router.post("/api/detect", response_model=AgentResponse)
async def detect_scam(payload: IncomingRequest, api_key_token: str = Security(api_key_header)):

    if api_key_token != API_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    message = payload.message or {}
    sender = (message.get("sender") or payload.sender or "scammer").lower()
    text = message.get("text") or payload.text or ""
    text = text if isinstance(text, str) else str(text)

    # session init (always)
    session_id = payload.session_id or str(uuid.uuid4())
    if session_id not in SESSION_START_TIMES:
        SESSION_START_TIMES[session_id] = time.time()
        SESSION_TURN_COUNT[session_id] = 0
        SESSION_SCAM_SCORE[session_id] = 0
        SESSION_COUNTS[session_id] = {"q": 0, "inv": 0, "rf": 0, "eli": 0}
        SESSION_ASKED[session_id] = set()
        db_create_session(session_id, SESSION_START_TIMES[session_id])  # ► persist

    # count this incoming scammer turn
    SESSION_TURN_COUNT[session_id] += 1
    turn = SESSION_TURN_COUNT[session_id]
    log_chat("Scammer", text)
    db_save_message(session_id, "scammer", text, turn)  # ► persist

    # small human jitter
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    # update risk score + preview extraction
    SESSION_SCAM_SCORE[session_id] += calculate_scam_score(text)
    preview = extract_intelligence(payload.conversation_history, text)
    hint = _next_hint(session_id, text, preview)
    db_upsert_indicators(session_id, preview)  # ► persist extracted indicators

    # LLM-first reply (paid key)
    reply = ""
    try:
        llm_out = await asyncio.to_thread(
            _llm_generate_reply,
            text,
            payload.conversation_history,
            hint,
            turn,
            SESSION_COUNTS[session_id],
        )
        reply = _sanitize_reply(llm_out)
    except Exception:
        reply = ""

    # absolute fallback if anything goes wrong
    if not reply:
        reply = "Okay, I'm a bit confused\u2014can you share the reference number for this?"

    # update running rubric feature counts
    feats = _count_features(reply)
    for k in ("q", "inv", "rf", "eli"):
        SESSION_COUNTS[session_id][k] += feats.get(k, 0)

    # tiny guardrail to avoid missing rubric thresholds (still LLM-driven overall)
    reply = _enforce_minimums(turn, reply, SESSION_COUNTS[session_id])
    log_chat("Honeypot", reply)
    db_save_message(session_id, "honeypot", reply, turn)  # ► persist
    db_update_session(  # ► persist session state
        session_id,
        turn_count=SESSION_TURN_COUNT[session_id],
        scam_score=SESSION_SCAM_SCORE[session_id],
        counts=SESSION_COUNTS[session_id],
        asked_hints=SESSION_ASKED.get(session_id, set()),
    )

    # finalization: always by turn 10, or earlier if enough intel
    final_obj = None
    if session_id not in FINAL_REPORTED:
        hv = high_value_count(preview)
        enough_intel = (hv >= 2) and (len(preview.get("referenceIds", []) or []) >= 1)

        if turn >= 10 or (turn >= 8 and enough_intel):
            FINAL_REPORTED.add(session_id)
            final_obj = build_final_output(session_id, payload.conversation_history, text)
            db_upsert_indicators(session_id, final_obj.get("extractedIntelligence", {}))  # ► persist final intel
            db_save_report(session_id, final_obj)  # ► persist report + mark completed

    return AgentResponse(
        status="success",
        reply=reply,
        finalCallback=final_obj,
        finalOutput=final_obj,
    )
