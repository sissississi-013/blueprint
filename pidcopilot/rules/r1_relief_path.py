"""R1 — Vessel has no relief path (API 521). RED. LEAD WITH THIS.

Missing-component rule -> corrective subgraph (ghost PSV + routing -> accept).
Reachability: vessel -> ... -> (PSV|RUPTURE_DISC) -> ... -> (FLARE|DISPOSAL),
traversing process edges undirected (relief routing can run either way through
valves). If no flare/disposal exists at all, we imply one (never throw).
"""
from __future__ import annotations

import networkx as nx

from ..graph.schema import Node, Edge, NodeType, PidGraph
from .base import Finding, Severity, GhostEdge, ProposedFix

RELIEF = {NodeType.PSV, NodeType.RUPTURE_DISC}
DISPOSAL = {NodeType.FLARE, NodeType.DISPOSAL}


class ReliefPathRule:
    id = "R1"
    requires = {"type"}

    def run(self, graph: PidGraph) -> list[Finding]:
        g = graph.to_nx().to_undirected()
        findings: list[Finding] = []

        relief_ids = {n.id for n in graph.nodes if n.type in RELIEF}
        disposal_ids = {n.id for n in graph.nodes if n.type in DISPOSAL}

        for vessel in graph.nodes_of(NodeType.VESSEL):
            if not g.has_node(vessel.id):
                continue
            reachable = nx.descendants(g, vessel.id) | {vessel.id}
            has_relief = bool(reachable & relief_ids)
            relief_to_disposal = any(
                _reaches(g, rid, disposal_ids) for rid in (reachable & relief_ids)
            )
            if has_relief and relief_to_disposal:
                continue  # protected

            tag = vessel.tag or vessel.id
            psv_tag = _mint_psv_tag(graph)
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


def _reaches(g, start, targets: set[str]) -> bool:
    return bool((nx.descendants(g, start) | {start}) & targets)


def _mint_psv_tag(graph: PidGraph) -> str:
    used = {n.tag for n in graph.nodes if n.tag and n.tag.upper().startswith("PSV")}
    i = 101
    while f"PSV-{i}" in used:
        i += 1
    return f"PSV-{i}"
