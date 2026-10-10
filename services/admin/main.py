"""Admin console (VM1) — the SOC analyst dashboard.

Serves a dashboard that subscribes to the engine's SSE stream and renders assessed
events live, highlighting anomalies. It proxies the engine's /stream and /stats so the
browser only talks to this origin.
"""
from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from shared.config import config

app = FastAPI(title="Secure Horizons — Admin Console")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/stats")
async def stats():
    async with httpx.AsyncClient(timeout=10) as http:
        try:
            r = await http.get(f"{config.ENGINE_URL}/stats")
            return r.json()
        except httpx.HTTPError:
            return {"total": 0, "by_verdict": {}, "alerts": 0, "engine": "offline"}


@app.get("/api/stream")
async def proxy_stream():
    """Proxy the engine's SSE stream to the dashboard (same-origin for the browser)."""

    async def gen():
        async with httpx.AsyncClient(timeout=None) as http:
            try:
                async with http.stream("GET", f"{config.ENGINE_URL}/stream") as r:
                    async for chunk in r.aiter_raw():
                        yield chunk
            except httpx.HTTPError:
                yield b"event: error\ndata: engine offline\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
