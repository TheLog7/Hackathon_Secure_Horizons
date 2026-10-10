"""SQLite persistence for assessed events, so the dashboard survives restarts."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from shared.config import config
from shared.models import AssessedEvent, Assessment, LogEvent


_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessed_events (
    event_id     TEXT PRIMARY KEY,
    employee_id  TEXT NOT NULL,
    timestamp    TEXT NOT NULL,
    verdict      TEXT NOT NULL,
    severity     TEXT NOT NULL,
    event_json   TEXT NOT NULL,
    assessment_json TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_assessed_created ON assessed_events(created_at);
"""


class Store:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def save(self, event: LogEvent, assessment: Assessment) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO assessed_events
                   (event_id, employee_id, timestamp, verdict, severity,
                    event_json, assessment_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.employee_id,
                    event.timestamp.isoformat(),
                    assessment.verdict,
                    assessment.severity,
                    event.model_dump_json(),
                    assessment.model_dump_json(),
                ),
            )

    def recent(self, limit: int = 100) -> list[AssessedEvent]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT event_json, assessment_json FROM assessed_events "
                "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            AssessedEvent(
                event=LogEvent.model_validate_json(r["event_json"]),
                assessment=Assessment.model_validate_json(r["assessment_json"]),
            )
            for r in rows
        ]

    def stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM assessed_events").fetchone()["c"]
            by_verdict = {
                r["verdict"]: r["c"]
                for r in conn.execute(
                    "SELECT verdict, COUNT(*) c FROM assessed_events GROUP BY verdict"
                ).fetchall()
            }
            alerts = conn.execute(
                "SELECT COUNT(*) c FROM assessed_events WHERE verdict='anomaly'"
            ).fetchone()["c"]
        return {"total": total, "by_verdict": by_verdict, "alerts": alerts}
