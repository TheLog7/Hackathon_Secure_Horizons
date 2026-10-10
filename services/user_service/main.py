"""User service (VM2) — the employee endpoint.

Serves a simple web UI where you pick an employee and click actions. Each click builds
a LogEvent and POSTs it to the detection engine, then shows the engine's verdict.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data import actions, company
from shared.config import config
from shared.models import LogEvent

app = FastAPI(title="Secure Horizons — User Endpoint")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class FireRequest(BaseModel):
    employee_id: str
    action_key: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/employees")
async def list_employees():
    out = []
    for e in company.employees():
        out.append(
            {
                "employee_id": e.employee_id,
                "name": e.name,
                "role": e.role,
                "department": e.department,
                "typical_hours": e.typical_hours,
                "agenda": [
                    {
                        "title": a.title,
                        "start": a.start.isoformat(),
                        "end": a.end.isoformat(),
                        "description": a.description,
                    }
                    for a in e.agenda
                ],
                "actions": [
                    {"key": a.key, "label": a.label, "kind": a.kind}
                    for a in actions.for_employee(e.employee_id)
                ],
            }
        )
    return out


@app.post("/api/fire")
async def fire_action(req: FireRequest):
    emp = company.by_id(req.employee_id)
    if emp is None:
        raise HTTPException(404, "unknown employee")
    template = next(
        (a for a in actions.for_employee(req.employee_id) if a.key == req.action_key),
        None,
    )
    if template is None:
        raise HTTPException(404, "unknown action")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    event = LogEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        employee_id=emp.employee_id,
        timestamp=today + timedelta(hours=template.hour, minutes=template.minute),
        action=template.action,
        resource=template.resource,
        source_ip=template.source_ip,
        bytes_out=template.bytes_out,
        details=template.details,
    )

    async with httpx.AsyncClient(timeout=60) as http:
        try:
            resp = await http.post(f"{config.ENGINE_URL}/events", json=event.model_dump(mode="json"))
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"engine unreachable: {exc}") from exc

    return resp.json()
