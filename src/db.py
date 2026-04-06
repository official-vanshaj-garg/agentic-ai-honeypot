import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Set

from sqlmodel import Session, SQLModel, create_engine, select

from src.models import (
    SessionRecord, Message, Indicator, SessionIndicator, Report,
)

# ============================================================
# DATABASE ENGINE
# ============================================================

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
DB_DIR = os.path.join(_PROJECT_ROOT, "data")
DB_PATH = os.path.join(DB_DIR, "agentic_ai_honeypot.db")
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, echo=False)


def create_db():
    """Create the data/ directory and all tables."""
    os.makedirs(DB_DIR, exist_ok=True)
    SQLModel.metadata.create_all(engine)


# ============================================================
# INDICATOR NORMALISATION
# ============================================================

EXTRACTION_KEY_TO_TYPE = {
    "phoneNumbers": "phone",
    "bankAccounts": "bank_account",
    "upiIds": "upi",
    "phishingLinks": "phishing_link",
    "emailAddresses": "email",
    "referenceIds": "reference_id",
}


def _normalize_value(indicator_type: str, value: str) -> str:
    """Normalise an indicator value before storage."""
    if indicator_type == "upi":
        return value.lower()
    if indicator_type == "phishing_link":
        return value.lower().rstrip("/")
    if indicator_type == "email":
        return value.lower()
    # phone, bank_account, reference_id: already normalised by extraction
    return value


# ============================================================
# DB HELPER FUNCTIONS
# ============================================================


def db_create_session(session_id: str, started_at: float):
    """Insert a new session row."""
    try:
        with Session(engine) as db:
            record = SessionRecord(id=session_id, started_at=started_at)
            db.add(record)
            db.commit()
    except Exception as e:
        print(f"[DB] Error creating session: {e}")


def db_save_message(session_id: str, sender: str, text: str, turn_number: int):
    """Insert a message row."""
    try:
        with Session(engine) as db:
            msg = Message(
                session_id=session_id,
                sender=sender,
                text=text,
                turn_number=turn_number,
            )
            db.add(msg)
            db.commit()
    except Exception as e:
        print(f"[DB] Error saving message: {e}")


def db_update_session(
    session_id: str,
    turn_count: int,
    scam_score: int,
    counts: Dict[str, int],
    asked_hints: Set[str],
    status: str = "active",
):
    """Update session fields after a turn is fully processed."""
    try:
        with Session(engine) as db:
            record = db.get(SessionRecord, session_id)
            if record:
                record.turn_count = turn_count
                record.scam_score = scam_score
                record.rubric_q = counts.get("q", 0)
                record.rubric_inv = counts.get("inv", 0)
                record.rubric_rf = counts.get("rf", 0)
                record.rubric_eli = counts.get("eli", 0)
                record.asked_hints = ",".join(sorted(asked_hints))
                record.status = status
                record.updated_at = datetime.now(timezone.utc)
                db.add(record)
                db.commit()
    except Exception as e:
        print(f"[DB] Error updating session: {e}")


def db_upsert_indicators(session_id: str, extracted: Dict[str, List[str]]):
    """
    Upsert indicators and create session-indicator links.

    CORRECTNESS RULE: hit_count counts DISTINCT SESSIONS.
    - New indicator globally → create with hit_count=1, link to session.
    - Known indicator, new session → increment hit_count, link to session.
    - Known indicator, already linked to this session → do nothing.
    """
    try:
        with Session(engine) as db:
            for ext_key, ind_type in EXTRACTION_KEY_TO_TYPE.items():
                values = extracted.get(ext_key) or []
                for raw_value in values:
                    if not raw_value:
                        continue
                    norm_val = _normalize_value(ind_type, raw_value)

                    # Find existing indicator
                    stmt = select(Indicator).where(
                        Indicator.indicator_type == ind_type,
                        Indicator.value == norm_val,
                    )
                    indicator = db.exec(stmt).first()

                    if indicator is None:
                        # New indicator — create it and link
                        indicator = Indicator(
                            indicator_type=ind_type,
                            value=norm_val,
                            hit_count=1,
                        )
                        db.add(indicator)
                        db.flush()  # assign id
                        link = SessionIndicator(
                            session_id=session_id,
                            indicator_id=indicator.id,
                        )
                        db.add(link)
                    else:
                        # Check if already linked to this session
                        link_stmt = select(SessionIndicator).where(
                            SessionIndicator.session_id == session_id,
                            SessionIndicator.indicator_id == indicator.id,
                        )
                        existing_link = db.exec(link_stmt).first()

                        if existing_link is None:
                            # New session for known indicator
                            indicator.hit_count += 1
                            indicator.last_seen_at = datetime.now(timezone.utc)
                            db.add(indicator)
                            link = SessionIndicator(
                                session_id=session_id,
                                indicator_id=indicator.id,
                            )
                            db.add(link)
                        # else: already linked — do nothing

            db.commit()
    except Exception as e:
        print(f"[DB] Error upserting indicators: {e}")


def db_save_report(session_id: str, final_obj: dict):
    """Insert a report row and mark the session as completed."""
    try:
        with Session(engine) as db:
            report = Report(
                session_id=session_id,
                scam_type=final_obj.get("scamType", "unknown"),
                confidence=float(final_obj.get("confidenceLevel", 0.0)),
                total_messages=int(final_obj.get("totalMessagesExchanged", 0)),
                duration_seconds=int(final_obj.get("engagementDurationSeconds", 0)),
                full_report_json=json.dumps(final_obj),
            )
            db.add(report)

            # Mark session completed
            record = db.get(SessionRecord, session_id)
            if record:
                record.status = "completed"
                record.updated_at = datetime.now(timezone.utc)
                db.add(record)

            db.commit()
    except Exception as e:
        print(f"[DB] Error saving report: {e}")
