import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select

from src.config import API_SECRET_TOKEN
from src.db import engine, EXTRACTION_KEY_TO_TYPE
from src.models import (
    SessionRecord, Message, Indicator, SessionIndicator, Report,
)

# ============================================================
# AUTH (same mechanism as POST /api/detect)
# ============================================================

_api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def _require_api_key(api_key: str = Depends(_api_key_header)):
    """Validate x-api-key header. Raises 403 on mismatch."""
    if api_key != API_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API Key")


# ============================================================
# READ-ONLY RETRIEVAL ENDPOINTS
# ============================================================

retrieval_router = APIRouter(dependencies=[Depends(_require_api_key)])

# Reverse map: indicator_type -> extraction key (camelCase)
_TYPE_TO_EXT_KEY = {v: k for k, v in EXTRACTION_KEY_TO_TYPE.items()}


def _iso(dt: Any) -> str:
    """Convert a datetime to ISO-8601 string, or return empty string."""
    if dt is None:
        return ""
    return dt.isoformat()


def _parse_asked_hints(raw: str) -> List[str]:
    """Convert comma-separated asked_hints string to a clean list."""
    if not raw or not raw.strip():
        return []
    return [h.strip() for h in raw.split(",") if h.strip()]


# ------------------------------------------------------------------
# GET /api/sessions
# ------------------------------------------------------------------

@retrieval_router.get("/api/sessions")
def list_sessions():
    with Session(engine) as db:
        stmt = select(SessionRecord).order_by(SessionRecord.updated_at.desc())
        sessions = db.exec(stmt).all()

        # Collect session IDs that have reports
        report_stmt = select(Report.session_id)
        reported_ids = set(db.exec(report_stmt).all())

        result = []
        for s in sessions:
            result.append({
                "sessionId": s.id,
                "sessionStatus": s.status,
                "turnCount": s.turn_count,
                "scamScore": s.scam_score,
                "startedAt": s.started_at,
                "createdAt": _iso(s.created_at),
                "updatedAt": _iso(s.updated_at),
                "hasReport": s.id in reported_ids,
            })

    return {"status": "success", "sessions": result}


# ------------------------------------------------------------------
# GET /api/sessions/{session_id}
# ------------------------------------------------------------------

@retrieval_router.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    with Session(engine) as db:
        record = db.get(SessionRecord, session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Session not found")

        # Session info
        session_data = {
            "sessionId": record.id,
            "sessionStatus": record.status,
            "turnCount": record.turn_count,
            "scamScore": record.scam_score,
            "rubricCounts": {
                "q": record.rubric_q,
                "inv": record.rubric_inv,
                "rf": record.rubric_rf,
                "eli": record.rubric_eli,
            },
            "askedHints": _parse_asked_hints(record.asked_hints),
            "startedAt": record.started_at,
            "createdAt": _iso(record.created_at),
            "updatedAt": _iso(record.updated_at),
        }

        # Messages sorted by turn_number ASC, then id ASC for stable tie-break
        msg_stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.turn_number.asc(), Message.id.asc())
        )
        messages = db.exec(msg_stmt).all()
        messages_data = [
            {
                "sender": m.sender,
                "text": m.text,
                "turnNumber": m.turn_number,
                "timestamp": _iso(m.timestamp),
            }
            for m in messages
        ]

        # Indicators for this session, grouped by extraction key
        ind_stmt = (
            select(Indicator)
            .join(SessionIndicator, SessionIndicator.indicator_id == Indicator.id)
            .where(SessionIndicator.session_id == session_id)
        )
        indicators = db.exec(ind_stmt).all()

        indicators_grouped: Dict[str, List[str]] = {
            "phoneNumbers": [],
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "emailAddresses": [],
            "referenceIds": [],
        }
        for ind in indicators:
            ext_key = _TYPE_TO_EXT_KEY.get(ind.indicator_type)
            if ext_key and ext_key in indicators_grouped:
                indicators_grouped[ext_key].append(ind.value)

        # Report availability
        report_stmt = select(Report).where(Report.session_id == session_id)
        report = db.exec(report_stmt).first()

    return {
        "status": "success",
        "session": session_data,
        "messages": messages_data,
        "indicators": indicators_grouped,
        "reportAvailable": report is not None,
    }


# ------------------------------------------------------------------
# GET /api/reports/{session_id}
# ------------------------------------------------------------------

@retrieval_router.get("/api/reports/{session_id}")
def get_report(session_id: str):
    with Session(engine) as db:
        # Verify session exists
        record = db.get(SessionRecord, session_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Session not found")

        stmt = select(Report).where(Report.session_id == session_id)
        report = db.exec(stmt).first()
        if report is None:
            raise HTTPException(
                status_code=404, detail="Report not found for session"
            )

        # Parse the stored JSON string back to a dict
        try:
            report_data = json.loads(report.full_report_json)
        except (json.JSONDecodeError, TypeError):
            report_data = {}

    return {
        "status": "success",
        "reportCreatedAt": _iso(report.created_at),
        "report": report_data,
    }


# ------------------------------------------------------------------
# GET /api/indicators
# ------------------------------------------------------------------

@retrieval_router.get("/api/indicators")
def list_indicators():
    with Session(engine) as db:
        stmt = select(Indicator).order_by(
            Indicator.hit_count.desc(),
            Indicator.last_seen_at.desc(),
        )
        indicators = db.exec(stmt).all()

        result = [
            {
                "type": ind.indicator_type,
                "value": ind.value,
                "hitCount": ind.hit_count,
                "firstSeenAt": _iso(ind.first_seen_at),
                "lastSeenAt": _iso(ind.last_seen_at),
            }
            for ind in indicators
        ]

    return {"status": "success", "indicators": result}
