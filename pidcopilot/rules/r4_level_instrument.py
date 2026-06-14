"""R4 — Vessel missing level instrument (Schulze Balhorn Rule 9, mandatory). RED.

Missing-component rule -> corrective subgraph (ghost level instrument -> accept).
A vessel should have an adjacent INSTRUMENT whose measured variable is level (L).
We detect "level" via the ISA tag parser (first letter == 'L') or an explicit
measured_var attr. Adjacency uses the undirected graph (instrument signal lines).
"""
from __future__ import annotations

from ..graph.schema import Node, Edge, NodeType, PidGraph
from .base import Finding, Severity, GhostEdge, ProposedFix, measured_var_of


class LevelInstrumentRule:
    id = "R4"
    requires = {"type"}

    def run(self, graph: PidGraph) -> list[Finding]:
        g = graph.to_nx().to_undirected()
        findings: list[Finding] = []

        for vessel in graph.nodes_of(NodeType.VESSEL):
            if not g.has_node(vessel.id):
                continue
            has_level = False
            for nbr in g.neighbors(vessel.id):
                n = graph.node(nbr)
                if not n or n.type != NodeType.INSTRUMENT:
                    continue
                mv = n.measured_var or measured_var_of(n.tag)
                if mv == "L":
                    has_level = True
                    break
            if has_level:
                continue

            tag = vessel.tag or vessel.id
            lit_tag = _mint_level_tag(graph)
            implied = Node(id=f"ghost-{lit_tag}", type=NodeType.INSTRUMENT,
                           tag=lit_tag, measured_var="L",
                           label=f"{lit_tag} (proposed)")
            findings.append(Finding(
                rule_id=self.id,
                severity=Severity.RED,
                node_ids=[vessel.id],
                message=f"{tag} has no level instrument",
                standard_ref="Schulze Balhorn R9 / good practice",
                ghost_edges=[GhostEdge(source=vessel.id, implied_node=implied)],
                fix=ProposedFix(
                    kind="add_subgraph",
                    summary=f"Add level instrument {lit_tag} on {tag}",
                    add_nodes=[implied],
                    add_edges=[Edge(id=f"e-{vessel.id}-{lit_tag}",
                                    source=vessel.id, target=implied.id)],
                ),
            ))
        return findings


def _mint_level_tag(graph: PidGraph) -> str:
    used = {n.tag for n in graph.nodes if n.tag and n.tag.upper().startswith("LIT")}
    i = 101
    while f"LIT-{i}" in used:
        i += 1
    return f"LIT-{i}"
