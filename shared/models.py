"""Pydantic models shared across the three services."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["info", "low", "medium", "high", "critical"]
Verdict = Literal["normal", "suspicious", "anomaly"]


class LogEvent(BaseModel):
    """A single action emitted by an employee endpoint (the user service)."""

    event_id: str
    employee_id: str
    timestamp: datetime
    action: str                 # e.g. "login", "db_access", "data_export"
    resource: str               # e.g. "finance-db", "customer-db"
    source_ip: str
    bytes_out: int = 0
    details: str = ""


class AgendaEntry(BaseModel):
    title: str
    start: datetime
    end: datetime
    description: str = ""


class Employee(BaseModel):
    employee_id: str
    name: str
    role: str
    department: str
    typical_hours: str                     # human-readable, e.g. "09:00-18:00"
    baseline_summary: str                  # 2-week behavioural baseline, in words
    usual_resources: list[str] = Field(default_factory=list)
    agenda: list[AgendaEntry] = Field(default_factory=list)


class Assessment(BaseModel):
    """The engine's (Claude's) verdict on a single event."""

    event_id: str
    employee_id: str
    timestamp: datetime
    verdict: Verdict
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    agenda_justified: bool = False
    agenda_reference: Optional[str] = None
    reasoning: str = ""
    recommended_action: str = ""
    model_used: str = ""


class AssessedEvent(BaseModel):
    """A log event paired with its assessment — what the admin console displays."""

    event: LogEvent
    assessment: Assessment
