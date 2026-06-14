"""PID2Graph .graphml -> canonical graph. TOPOLOGY-ONLY (build-plan §2/§6.1).

PID2Graph's 7 coarse classes carry no instrument tags, so source_fidelity is
"topology": tag/fail_position stay None and rules requiring them self-skip (no
false positives). Used for visual realism + ingest/diff plumbing tests.
"""
from __future__ import annotations

import networkx as nx

from ..graph.schema import Node, Edge, NodeType, EdgeKind, PidGraph

# PID2Graph symbol classes -> coarse NodeType
CLASS_MAP = {
    "tank": NodeType.VESSEL, "vessel": NodeType.VESSEL, "tank/vessel": NodeType.VESSEL,
    "pump": NodeType.PUMP, "compressor": NodeType.PUMP, "pump/compressor": NodeType.PUMP,
    "instrumentation": NodeType.INSTRUMENT, "instrument": NodeType.INSTRUMENT,
    "valve": NodeType.BLOCK_VALVE,
    "arrow": NodeType.GENERIC, "inlet/outlet": NodeType.INLET,
    "general": NodeType.GENERIC,
}


def load_graphml(path: str) -> PidGraph:
    g = nx.read_graphml(path)
    nodes: list[Node] = []
    for nid, attrs in g.nodes(data=True):
        label = str(attrs.get("label", attrs.get("class", ""))).lower()
        nt = CLASS_MAP.get(label, NodeType.UNKNOWN)
        nodes.append(Node(id=str(nid), type=nt, label=label or None,
                          source_fidelity="topology"))
    edges: list[Edge] = []
    for i, (s, t, attrs) in enumerate(g.edges(data=True)):
        line = str(attrs.get("label", attrs.get("class", "solid"))).lower()
        kind = EdgeKind.SIGNAL if "non" in line or "dash" in line else EdgeKind.PROCESS
        edges.append(Edge(id=f"e{i}", source=str(s), target=str(t), kind=kind))
    return PidGraph(source="graphml", nodes=nodes, edges=edges)
