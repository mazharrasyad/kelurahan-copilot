"""Web front end for the cross-system copilot (FastAPI)."""
import logging
import os
import time
from collections import deque
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import agent

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="Kelurahan Copilot", docs_url=None, redoc_url=None)
HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = (os.environ.get("BASE_PATH") or "/").rstrip("/") + "/"
PER_MIN = int(os.environ.get("ASK_PER_MIN", "6"))
PER_DAY = int(os.environ.get("ASK_PER_DAY", "300"))
_hits: dict[str, deque] = {}
_day: deque = deque()


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    history: list[dict] = Field(default_factory=list, max_length=12)


def _limit(ip: str):
    now = time.time()
    q = _hits.setdefault(ip, deque())
    while q and now - q[0] > 60:
        q.popleft()
    while _day and now - _day[0] > 86400:
        _day.popleft()
    if len(q) >= PER_MIN or len(_day) >= PER_DAY:
        raise HTTPException(429, "Too many questions right now, please wait a minute.")
    q.append(now)
    _day.append(now)


@app.get("/")
def index():
    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read().replace('<base href="/">', f'<base href="{BASE_PATH}">')
    return HTMLResponse(html, headers={"cache-control": "no-store"})


@app.get("/api/tools")
async def tools():
    """The tools each Synapse-generated MCP server exposes right now."""
    return {"systems": {k: {"label": c["label"]} for k, c in agent.SYSTEMS.items()},
            "tools": await agent.list_tools_only(), "model": agent.LLM_MODEL, "llm": bool(agent.LLM_KEY)}


@app.post("/api/ask")
async def ask(body: Ask, request: Request):
    _limit((request.headers.get("x-forwarded-for") or request.client.host).split(",")[0].strip())
    try:
        r = await agent.ask(body.question.strip(), body.history)
    except Exception as e:
        root = e
        while isinstance(root, BaseExceptionGroup) and root.exceptions:
            root = root.exceptions[0]
        log.error("ask failed", exc_info=root)
        raise HTTPException(502, f"Agent error: {type(root).__name__}: {str(root)[:300]}")
    if r.error:
        raise HTTPException(503, r.error)
    return asdict(r)


@app.get("/health")
def health():
    return {"ok": True}
