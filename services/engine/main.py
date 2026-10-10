"""Detection engine — the 'NDR model'.

Receives log events from the user service, loads the employee's baseline + agenda,
asks Claude (Bedrock) for a verdict, persists it, and broadcasts assessed events to
subscribers (the admin console) over Server-Sent Events.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from data import company
from services.engine.bedrock_client import BedrockClient
from shared.config import config
from shared.models import AssessedEvent, LogEvent
from shared.store import Store

store = Store()
client = BedrockClient()

# Fan-out queues for SSE subscribers (the admin console tabs).
_subscribers: set[asyncio.Queue] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = "REAL Bedrock" if config.USE_REAL_BEDROCK else "STUB"
    print(f"[engine] starting | mode={mode} | model={client.model_id} | region={config.AWS_REGION}")
    yield


app = FastAPI(title="Secure Horizons — Detection Engine", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _broadcast(assessed: AssessedEvent) -> None:
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(assessed)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.discard(q)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "real" if config.USE_REAL_BEDROCK else "stub",
        "model": client.model_id,
        "region": config.AWS_REGION,
        "subscribers": len(_subscribers),
    }


@app.post("/events", response_model=AssessedEvent)
async def ingest_event(event: LogEvent):
    employee = company.by_id(event.employee_id)
    if employee is None:
        raise HTTPException(404, f"unknown employee {event.employee_id}")

    # Claude's assessment can block, so run it off the event loop.
    assessment = await asyncio.to_thread(client.assess, employee, event)
    store.save(event, assessment)

    assessed = AssessedEvent(event=event, assessment=assessment)
    await _broadcast(assessed)
    return assessed


@app.get("/assessments")
async def list_assessments(limit: int = 100):
    return [a.model_dump(mode="json") for a in store.recent(limit)]


@app.get("/stats")
async def stats():
    return store.stats()


@app.get("/stream")
async def stream():
    """SSE stream of assessed events for the admin console."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _subscribers.add(queue)

    async def event_gen():
        try:
            # replay recent history first so a freshly opened dashboard isn't empty
            for assessed in reversed(store.recent(50)):
                yield {"event": "assessment", "data": assessed.model_dump_json()}
            while True:
                assessed = await queue.get()
                yield {"event": "assessment", "data": assessed.model_dump_json()}
        finally:
            _subscribers.discard(queue)

    return EventSourceResponse(event_gen())
