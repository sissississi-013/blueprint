"""R5 (pump protection set) + R6 (ISA-5.1 tag grammar) — STRETCH rules (§5.3).

Not in the default engine. Wire into default_rules() only if green by H8.5.
Kept here so the scope cut is explicit and the code is ready if there's time.
"""
from __future__ import annotations

from ..graph.schema import Node, Edge, NodeType, PidGraph
from .base import Finding, Severity, GhostEdge, ProposedFix, parse_tag, MEASURED_VARS


class PumpProtectionRule:
    id = "R5"
    requires = {"type"}

    def run(self, graph: PidGraph) -> list[Finding]:
        g = graph.to_nx()
        findings: list[Finding] = []
        for pump in graph.nodes_of(NodeType.PUMP):
            succ = {graph.node(t).type for _, t in g.out_edges(pump.id) if graph.node(t)}
            pred = {graph.node(s).type for s, _ in g.in_edges(pump.id) if graph.node(s)}
            tag = pump.tag or pump.id
            if NodeType.CHECK_VALVE not in succ:
                findings.append(_amber(self.id, pump.id,
                    f"{tag} discharge has no check valve (backflow risk)", "Rule 19"))
            if NodeType.STRAINER not in pred:
                findings.append(_amber(self.id, pump.id,
                    f"{tag} suction has no strainer", "Rule 10"))
        return findings


class IsaTagGrammarRule:
    id = "R6"
    requires = {"tag"}

    def run(self, graph: PidGraph) -> list[Finding]:
        findings: list[Finding] = []
        for n in graph.nodes:
            if not n.tag:
                continue
            p = parse_tag(n.tag)
            if p is None:
                findings.append(_amber(self.id, n.id,
                    f"Tag '{n.tag}' does not match ISA-5.1 grammar", "ISA-5.1"))
            elif p["first"] not in MEASURED_VARS:
                findings.append(_amber(self.id, n.id,
                    f"Tag '{n.tag}' has an invalid measured-variable first letter", "ISA-5.1"))
        return findings


def _amber(rule_id, node_id, message, ref):
    return Finding(rule_id=rule_id, severity=Severity.AMBER, node_ids=[node_id],
                   message=message, standard_ref=ref)
