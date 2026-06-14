"""FastAPI service — the brain. Owns the autonomy heartbeat (build-plan §0b #1):
a Python watcher drives ingest -> validate -> annotate -> alert, so autonomy does
NOT depend on OpenClaw's trigger. OpenClaw is the agent face (Q&A/narration/Telegram).

Run:  uvicorn pidcopilot.server:app --host 127.0.0.1 --port 8000
Pane: open web/index.html (it connects to ws://127.0.0.1:8000/ws)
"""
from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .graph.diff import regression_messages
from .graph.schema import NodeType, PidGraph
from .ingest import ingest
from .rules.engine import apply_fix, default_engine
from .demo.synthetic import build_clean_graph
from .demo import revisions as demo_revisions
from .llm import nemotron
from .alerts import telegram

app = FastAPI(title="P&ID Copilot")
engine = default_engine()


class State:
    """In-memory current graph + last findings + ws clients."""
    def __init__(self):
        self.graph: PidGraph = build_clean_graph()
        self.findings: list = []
        self.clients: set[WebSocket] = set()

    async def broadcast(self, msg: dict):
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(json.dumps(msg))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


state = State()


def _report() -> dict:
    rep = engine.report(state.graph)
    state.findings = engine.run(state.graph)
    return rep


async def push_graph():
    await state.broadcast({"type": "graph", "graph": state.graph.model_dump()})


async def push_annotations(regressions: list[str] | None = None):
    rep = _report()
    await state.broadcast({
        "type": "annotations",
        "revision": state.graph.revision,
        "checks_run": rep["checks_run"],
        "passing": rep["passing"],
        "issues": rep["issues"],
        "findings": rep["findings"],
        "regressions": regressions or [],
    })
    reds = [f for f in rep["findings"] if f["severity"] == "red"]
    if reds or regressions:
        telegram.send(telegram.format_alert(state.graph.revision, reds, regressions or []))


async def set_graph(new_graph: PidGraph):
    old = state.graph
    state.graph = new_graph
    regressions = regression_messages(old, new_graph)
    await push_graph()
    await push_annotations(regressions)


# --- HTTP endpoints --------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "graph_loaded": bool(state.graph.nodes),
        "revision": state.graph.revision,
        "rules": [r.id for r in engine.rules],
    }


@app.post("/ingest")
async def http_ingest(payload: dict):
    path = payload.get("path")
    g = ingest(path)
    g.revision = state.graph.revision + 1
    await set_graph(g)
    return {"revision": g.revision, "nodes": len(g.nodes), "edges": len(g.edges),
            "source": g.source}


@app.post("/validate")
async def http_validate():
    rep = _report()
    return rep


@app.post("/revision")
async def http_revision(payload: dict):
    name = payload.get("name")
    try:
        new = demo_revisions.apply_named_revision(name, state.graph)
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    await set_graph(new)
    return {"revision": new.revision, "applied": name}


@app.post("/explain")
def http_explain(payload: dict):
    rule_id = payload.get("rule_id")
    finding = next((f for f in state.findings if f.rule_id == rule_id), None)
    if not finding:
        return {"text": "No active finding for that rule."}
    return {"text": nemotron.narrate(finding.model_dump())}


@app.post("/ask")
def http_ask(payload: dict):
    q = (payload.get("text") or "").lower()
    # Deterministic GraphRAG-lite: compute the answer, let the LLM only phrase it.
    if "relief" in q or "protect" in q:
        protected, unprotected = _vessels_relief_split()
        result = (f"Protected vessels: {', '.join(protected) or 'none'}. "
                  f"Unprotected: {', '.join(unprotected) or 'none'}.")
        highlight = protected
    elif "level" in q:
        ids = [n.tag or n.id for n in state.graph.nodes_of(NodeType.INSTRUMENT)
               if (n.measured_var == "L")]
        result = f"Level instruments: {', '.join(ids) or 'none'}."
        highlight = ids
    else:
        result = "Ask about relief protection or level instruments (demo scope)."
        highlight = []
    return {"answer": nemotron.answer(payload.get("text", ""), result),
            "highlight_node_ids": highlight}


@app.post("/accept_fix")
async def http_accept_fix(payload: dict):
    rule_id = payload.get("rule_id")
    finding = next((f for f in state.findings if f.rule_id == rule_id and f.fix), None)
    if not finding:
        return JSONResponse({"error": "no fixable finding for that rule"}, status_code=400)
    new = apply_fix(state.graph, finding.fix)
    await set_graph(new)
    rep = engine.report(new)
    return {"revision": new.revision, "applied_fix": finding.fix.summary,
            "passing": rep["passing"], "issues": rep["issues"]}


def _vessels_relief_split():
    from .rules.r1_relief_path import ReliefPathRule
    unprotected_ids = {fid for f in ReliefPathRule().run(state.graph) for fid in f.node_ids}
    protected, unprotected = [], []
    for v in state.graph.nodes_of(NodeType.VESSEL):
        (unprotected if v.id in unprotected_ids else protected).append(v.tag or v.id)
    return protected, unprotected


# --- WebSocket -------------------------------------------------------------------

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    state.clients.add(websocket)
    await websocket.send_text(json.dumps({"type": "graph", "graph": state.graph.model_dump()}))
    rep = _report()
    await websocket.send_text(json.dumps({
        "type": "annotations", "revision": state.graph.revision,
        "checks_run": rep["checks_run"], "passing": rep["passing"],
        "issues": rep["issues"], "findings": rep["findings"], "regressions": [],
    }))
    try:
        while True:
            data = json.loads(await websocket.receive_text())
            await _handle_ws(data)
    except WebSocketDisconnect:
        state.clients.discard(websocket)


async def _handle_ws(data: dict):
    t = data.get("type")
    if t == "apply_revision":
        with contextlib.suppress(KeyError):
            await set_graph(demo_revisions.apply_named_revision(data["name"], state.graph))
    elif t == "accept_fix":
        finding = next((f for f in state.findings
                        if f.rule_id == data.get("rule_id") and f.fix), None)
        if finding:
            await set_graph(apply_fix(state.graph, finding.fix))
    elif t == "ask":
        # reuse the HTTP logic
        res = http_ask({"text": data.get("text", "")})
        await state.broadcast({"type": "highlight", "node_ids": res["highlight_node_ids"],
                               "answer": res["answer"]})
    elif t == "why":
        res = http_explain({"rule_id": data.get("rule_id")})
        await state.broadcast({"type": "explanation", "rule_id": data.get("rule_id"),
                               "text": res["text"]})


# --- Python-owned autonomy heartbeat: watch the saved-revisions folder ----------

async def _watch_loop():
    seen: dict[str, float] = {}
    watch = Path(config.WATCH_DIR)
    watch.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            for p in sorted(watch.glob("*")):
                if p.suffix.lower() not in (".drawio", ".xml", ".graphml"):
                    continue
                mtime = p.stat().st_mtime
                if seen.get(str(p)) == mtime:
                    continue
                seen[str(p)] = mtime
                g = ingest(str(p))
                if g.nodes:
                    g.revision = state.graph.revision + 1
                    await set_graph(g)
        except Exception:
            pass
        await asyncio.sleep(config.WATCH_POLL_SECONDS)


@app.on_event("startup")
async def _startup():
    app.state.watcher = asyncio.create_task(_watch_loop())


# Static pane (served locally; nothing leaves the box)
if config.WEB_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")


@app.get("/")
def index():
    idx = config.WEB_DIR / "index.html"
    return FileResponse(str(idx)) if idx.exists() else {"service": "pidcopilot"}
