"""PDF/image -> graph via Nemotron Nano-12B-VL. STRETCH (invisibility proof).

Goal: ONE hand-checked PDF round-trips to a review; accuracy is not graded, the
gesture is. Keep a frozen fallback graph for the demo PDF in fixtures/.
This is a thin stub: it asks the VLM for structured {symbols, lines} JSON and
builds a canonical graph. Wire to the real model on-site (build-plan §6.4).
"""
from __future__ import annotations

import json
import os

from ..graph.schema import Node, Edge, NodeType, EdgeKind, PidGraph

VLM_PROMPT = (
    "You are reading a Piping & Instrumentation Diagram. Return STRICT JSON only:\n"
    '{"symbols":[{"id":"n1","type":"vessel|pump|control_valve|psv|flare|instrument",'
    '"tag":"V-101"}],"lines":[{"source":"n1","target":"n2"}]}\n'
    "Do not infer anything not visibly present."
)


def load_vision(path: str, fixtures_dir: str | None = None) -> PidGraph:
    # Safety net: if a frozen fallback exists for this artifact, use it.
    if fixtures_dir:
        frozen = os.path.join(fixtures_dir, os.path.basename(path) + ".graph.json")
        if os.path.exists(frozen):
            with open(frozen) as f:
                return PidGraph.model_validate_json(f.read())

    from ..llm.nemotron import vision_extract  # lazy; needs a running VL model
    raw = vision_extract(path, VLM_PROMPT)
    data = _coerce_json(raw)
    nodes = [Node(id=s["id"], type=_safe_type(s.get("type")), tag=s.get("tag"),
                  label=s.get("tag"), source_fidelity="rich")
             for s in data.get("symbols", [])]
    edges = [Edge(id=f"e{i}", source=l["source"], target=l["target"],
                  kind=EdgeKind.PROCESS)
             for i, l in enumerate(data.get("lines", []))]
    return PidGraph(source="vision", nodes=nodes, edges=edges)


def _safe_type(t: str | None) -> NodeType:
    try:
        return NodeType(t)
    except (ValueError, TypeError):
        return NodeType.UNKNOWN


def _coerce_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        return {"symbols": [], "lines": []}
