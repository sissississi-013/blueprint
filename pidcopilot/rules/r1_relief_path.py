"""R1 — Vessel has no relief path (API 521). RED. LEAD WITH THIS.

Missing-component rule -> corrective subgraph (ghost PSV + routing -> accept).
Reachability is per-vessel, over PROCESS edges only (signal/instrument lines are
not relief paths): vessel -> ... -> (PSV|RUPTURE_DISC) -> ... -> (FLARE|DISPOSAL).
Direction is honoured except *through valves* (build-plan R1) — a control/block
valve imposes no flow direction, so relief may route either way through it. The
same relief device must be reachable FROM the vessel AND itself reach a disposal,
so a PSV on a neighbouring vessel doesn't protect this one. If no flare/disposal
exists at all, we imply one (never throw).
"""
from __future__ import annotations

import networkx as nx

from ..graph.schema import Node, Edge, EdgeKind, NodeType, PidGraph
from .base import Finding, Severity, GhostEdge, ProposedFix

RELIEF = {NodeType.PSV, NodeType.RUPTURE_DISC}
DISPOSAL = {NodeType.FLARE, NodeType.DISPOSAL}
# Relief can flow either way through a hand/control valve, so we ignore edge
# direction at these nodes. CHECK_VALVE is excluded: blocking reverse flow is its
# whole function.
VALVE_PASSTHROUGH = {NodeType.CONTROL_VALVE, NodeType.BLOCK_VALVE}


class ReliefPathRule:
    id = "R1"
    requires = {"type"}

    def run(self, graph: PidGraph) -> list[Finding]:
        g = _process_digraph(graph)
        findings: list[Finding] = []

        relief_ids = {n.id for n in graph.nodes if n.type in RELIEF}
        disposal_ids = {n.id for n in graph.nodes if n.type in DISPOSAL}
        minted: set[str] = set()

        for vessel in graph.nodes_of(NodeType.VESSEL):
            if _is_protected(g, vessel.id, relief_ids, disposal_ids):
                continue  # protected

            tag = vessel.tag or vessel.id
            psv_tag = _mint_psv_tag(graph, minted)
            minted.add(psv_tag)
            implied_psv = Node(id=f"ghost-{psv_tag}", type=NodeType.PSV,
                               tag=psv_tag, label=f"{psv_tag} (proposed)")
            ghosts = [GhostEdge(source=vessel.id, implied_node=implied_psv)]

            # route to an existing disposal, else imply a flare too.
            disposal_target = next(iter(disposal_ids), None)
            add_nodes = [implied_psv]
            add_edges = [Edge(id=f"e-{vessel.id}-{psv_tag}", source=vessel.id,
                              target=implied_psv.id)]
            if disposal_target:
                ghosts.append(GhostEdge(source=implied_psv.id, target=disposal_target))
                add_edges.append(Edge(id=f"e-{psv_tag}-{disposal_target}",
                                      source=implied_psv.id, target=disposal_target))
                route_txt = f"route to {graph.node(disposal_target).tag or disposal_target}"
            else:
                flare = Node(id="ghost-FLARE", type=NodeType.FLARE, label="Flare (proposed)")
                ghosts.append(GhostEdge(source=implied_psv.id, implied_node=flare))
                add_nodes.append(flare)
                add_edges.append(Edge(id=f"e-{psv_tag}-flare", source=implied_psv.id,
                                      target=flare.id))
                route_txt = "route to a new flare (no disposal system found)"

            findings.append(Finding(
                rule_id=self.id,
                severity=Severity.RED,
                node_ids=[vessel.id],
                message=f"{tag} has no relief path to flare/disposal",
                standard_ref="API 521",
                ghost_edges=ghosts,
                fix=ProposedFix(
                    kind="add_subgraph",
                    summary=f"Add {psv_tag} on {tag} and {route_txt}",
                    add_nodes=add_nodes,
                    add_edges=add_edges,
                ),
            ))
        return findings


def _process_digraph(graph: PidGraph) -> nx.DiGraph:
    """Directed graph of PROCESS edges only (relief routing is physical piping,
    not signal/instrument lines). Edges incident to a pass-through valve are made
    bidirectional, since such a valve imposes no flow direction. Every node is
    added so lookups never KeyError."""
    valves = {n.id for n in graph.nodes if n.type in VALVE_PASSTHROUGH}
    g = nx.DiGraph()
    for n in graph.nodes:
        g.add_node(n.id)
    for e in graph.edges:
        if e.kind != EdgeKind.PROCESS:
            continue
        g.add_edge(e.source, e.target)
        if e.source in valves or e.target in valves:
            g.add_edge(e.target, e.source)
    return g


def _is_protected(g, vessel_id: str, relief_ids: set[str],
                  disposal_ids: set[str]) -> bool:
    """True iff some relief device is reachable FROM the vessel and itself reaches
    a disposal. The single device must satisfy both legs — a PSV on a neighbour
    doesn't count."""
    if not g.has_node(vessel_id):
        return False
    for rid in relief_ids:
        if not g.has_node(rid) or not nx.has_path(g, vessel_id, rid):
            continue
        if any(g.has_node(d) and nx.has_path(g, rid, d) for d in disposal_ids):
            return True
    return False


def _mint_psv_tag(graph: PidGraph, minted: frozenset[str] = frozenset()) -> str:
    """Next free PSV-NNN, avoiding both existing tags and ones already minted in
    this run, so multiple unprotected vessels each get a distinct PSV."""
    used = {n.tag for n in graph.nodes if n.tag and n.tag.upper().startswith("PSV")}
    used |= minted
    i = 101
    while f"PSV-{i}" in used:
        i += 1
    return f"PSV-{i}"
