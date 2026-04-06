from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# DATABASE MODELS
# ============================================================


class SessionRecord(SQLModel, table=True):
    """One row per conversation session."""

    __tablename__ = "session"

    id: str = Field(primary_key=True)
    started_at: float
    turn_count: int = 0
    scam_score: int = 0
    rubric_q: int = 0
    rubric_inv: int = 0
    rubric_rf: int = 0
    rubric_eli: int = 0
    asked_hints: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class Message(SQLModel, table=True):
    """Every message in every session (scammer and honeypot)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    sender: str
    text: str
    turn_number: int
    timestamp: datetime = Field(default_factory=_utc_now)


class Indicator(SQLModel, table=True):
    """Global registry of unique indicators across all sessions."""

    __table_args__ = (UniqueConstraint("indicator_type", "value"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    indicator_type: str
    value: str
    first_seen_at: datetime = Field(default_factory=_utc_now)
    last_seen_at: datetime = Field(default_factory=_utc_now)
    hit_count: int = 1


class SessionIndicator(SQLModel, table=True):
    """Links indicators to the sessions they were extracted from."""

    __tablename__ = "session_indicator"
    __table_args__ = (UniqueConstraint("session_id", "indicator_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    indicator_id: int = Field(foreign_key="indicator.id")
    extracted_at: datetime = Field(default_factory=_utc_now)


class Report(SQLModel, table=True):
    """Final report per session. One report per session."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", unique=True)
    scam_type: str
    confidence: float
    total_messages: int
    duration_seconds: int
    full_report_json: str
    created_at: datetime = Field(default_factory=_utc_now)
