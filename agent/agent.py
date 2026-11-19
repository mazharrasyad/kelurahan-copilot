"""Cross-system copilot: one LLM agent, two Synapse-generated MCP servers.

Every question opens fresh stdio sessions to both servers and lists their tools, so a
server rebuilt with `synapse build --discover` is picked up on the next question without
restarting anything. The LLM is any OpenAI-compatible chat API with tool calling (Groq by
default, free tier).
"""
from __future__ import annotations

import asyncio
import glob
import json
import os
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The two legacy systems. server = the file Synapse generated; base = where that system's API runs.
SYSTEMS = {
    "sipos": {
        "label": "SIPOS Posyandu",
        "server": os.environ.get("SIPOS_MCP", os.path.join(ROOT, "systems", "sipos-posyandu", "synapse_auto_server.py")),
        "base": os.environ.get("SIPOS_BASE_URL", "http://127.0.0.1:8101"),
        "about": "health posts (posyandu) and village-level nutrition recaps of toddlers; villages are identified by NAME (free text, field 'kelurahan')",
    },
    "sidbd": {
        "label": "SI-DBD",
        "server": os.environ.get("SIDBD_MCP", os.path.join(ROOT, "systems", "si-dbd", "synapse_auto_server.py")),
        "base": os.environ.get("SIDBD_BASE_URL", "http://127.0.0.1:8102"),
        "about": "dengue surveillance recaps and larva inspections; villages are identified by official CODE (kode_kelurahan); list_wilayah maps codes to village names",
    },
}

LLM_BASE = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("GROQ_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")
MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "10"))
MAX_TOOL_CHARS = 14000

SYSTEM_PROMPT = """You are Kelurahan Copilot, a public-health planning assistant for a district health office in Indonesia.
You can only see data through tools from two separate legacy systems that share no database:
{systems}
Rules:
- You only receive village-level aggregates. No personal data (NIK, names, addresses) is available or needed; never ask for it.
- The two systems name villages differently: join them by mapping SIPOS's village name to SI-DBD's kode_kelurahan with sidbd__list_wilayah (compare names case-insensitively). Show both the village name and code.
- Tools take no filters: fetch the recap and filter or rank it yourself. "Active" dengue cases = field aktif. At-risk toddlers = gizi kurang + gizi buruk + stunting. The larva-free index (ABJ) target is >= 95%; use the latest inspection per village.
- When asked to prioritise, rank by both signals together and explain the ranking in one line.
- Never invent records. If something is not in the tool results, say so.
- Answer in the user's language, concisely, with a short table or bullet list. For every fact, say which system it came from (SIPOS or SI-DBD).
- Use the minimum number of tool calls needed."""


@dataclass
class Step:
    system: str
    tool: str
    args: dict
    ok: bool
    summary: str
    ms: int


@dataclass
class Result:
    answer: str
    steps: list[Step] = field(default_factory=list)
    tools: dict = field(default_factory=dict)
    model: str = LLM_MODEL
    error: str | None = None


def _result_text(res) -> str:
    parts = [c.text for c in (res.content or []) if getattr(c, "type", "") == "text"]
    if not parts and res.structuredContent is not None:
        return json.dumps(res.structuredContent, ensure_ascii=False)
    if len(parts) > 1:  # FastMCP v1 returns one block per list item
        items = []
        for p in parts:
            try:
                items.append(json.loads(p))
            except ValueError:
                items.append(p)
        return json.dumps(items, ensure_ascii=False)
    return parts[0] if parts else "[]"


def _summary(text: str) -> str:
    try:
        v = json.loads(text)
        if isinstance(v, list):
            return f"{len(v)} records"
        if isinstance(v, dict):
            return ", ".join(list(v.keys())[:5])
    except ValueError:
        pass
    return text[:80]


def server_file(cfg: dict) -> str:
    """Newest Synapse output in the system's folder: a rebuild writes synapse_auto_server_N.py
    next to the old file instead of overwriting it, so the latest generation wins."""
    folder = os.path.dirname(cfg["server"])
    files = glob.glob(os.path.join(folder, "synapse_auto_server*.py"))
    return max(files, key=os.path.getmtime) if files else cfg["server"]


async def open_sessions(stack: AsyncExitStack):
    sessions, tools = {}, {}
    for key, cfg in SYSTEMS.items():
        params = StdioServerParameters(command=os.environ.get("PYTHON", "python"), args=[server_file(cfg)],
                                       env={**os.environ, "ENDPOINT_BASE_URL": cfg["base"]})
        r, w = await stack.enter_async_context(stdio_client(params))
        s = await stack.enter_async_context(ClientSession(r, w))
        await s.initialize()
        sessions[key] = s
        tools[key] = (await s.list_tools()).tools
    return sessions, tools


def openai_tools(tools: dict) -> list[dict]:
    out = []
    for key, lst in tools.items():
        for t in lst:
            out.append({"type": "function", "function": {
                "name": f"{key}__{t.name}",
                "description": f"[{SYSTEMS[key]['label']}] {t.description or t.name}",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            }})
    return out


async def chat(messages: list[dict], tools: list[dict]) -> dict:
    async with httpx.AsyncClient(timeout=90) as c:
        for attempt in range(3):
            r = await c.post(f"{LLM_BASE}/chat/completions", headers={"authorization": f"Bearer {LLM_KEY}"},
                             json={"model": LLM_MODEL, "messages": messages, "tools": tools, "tool_choice": "auto", "temperature": 0.1})
            if r.status_code == 429 and attempt < 2:
                await asyncio.sleep(float(r.headers.get("retry-after", "3")))
                continue
            if r.status_code == 400 and "tool_use_failed" in r.text and attempt < 2:
                continue  # the model emitted a malformed tool call; ask again
            if r.status_code >= 400:
                raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:300]}")
            return r.json()["choices"][0]["message"]
    raise RuntimeError("LLM rate limited")


async def list_tools_only() -> dict:
    async with AsyncExitStack() as stack:
        _, tools = await open_sessions(stack)
        return {k: [{"name": t.name, "description": t.description} for t in v] for k, v in tools.items()}


async def ask(question: str, history: list[dict] | None = None) -> Result:
    if not LLM_KEY:
        return Result(answer="", error="LLM_API_KEY is not configured on the server.")
    async with AsyncExitStack() as stack:
        sessions, tools = await open_sessions(stack)
        result = Result(answer="", tools={k: [t.name for t in v] for k, v in tools.items()})
        systems = "\n".join(f"- {k} ({c['label']}): {c['about']}" for k, c in SYSTEMS.items())
        messages = [{"role": "system", "content": SYSTEM_PROMPT.format(systems=systems)}]
        messages += [m for m in (history or []) if m.get("role") in ("user", "assistant")][-6:]
        messages.append({"role": "user", "content": question})
        spec = openai_tools(tools)
        for _ in range(MAX_STEPS):
            msg = await chat(messages, spec)
            calls = msg.get("tool_calls") or []
            if not calls:
                result.answer = msg.get("content") or ""
                return result
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for call in calls:
                name = call["function"]["name"]
                key, _, tool = name.partition("__")
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                except ValueError:
                    args = {}
                t0 = time.time()
                if key not in sessions:
                    text, ok = f"Unknown tool {name}", False
                else:
                    try:
                        res = await sessions[key].call_tool(tool, args)
                        text, ok = _result_text(res), not res.isError
                    except Exception as e:  # tool failed (e.g. 404 from the legacy API)
                        text, ok = f"Tool error: {e}", False
                result.steps.append(Step(system=SYSTEMS.get(key, {}).get("label", key), tool=tool, args=args, ok=ok,
                                         summary=_summary(text), ms=int((time.time() - t0) * 1000)))
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": text[:MAX_TOOL_CHARS]})
        result.answer = "I could not finish within the step limit. Please narrow the question."
        return result
