"""Rule engine + apply_fix. Deterministic, full-scan (diff-as-scoping cut per §0b).

apply_fix() is the suggest-the-fix core: promote ghost nodes -> real, add edges,
set attrs, or rename — producing a new revision the pane re-validates.
"""
from __future__ import annotations

from ..graph.schema import PidGraph
from .base import Finding, Severity, ProposedFix
from .r1_relief_path import ReliefPathRule
from .r2_duplicate_tag import DuplicateTagRule
from .r3_fail_position import FailPositionRule
from .r4_level_instrument import LevelInstrumentRule


class RuleEngine:
    def __init__(self, rules: list | None = None):
        self.rules = rules if rules is not None else default_rules()

    def run(self, graph: PidGraph) -> list[Finding]:
        findings: list[Finding] = []
        for rule in self.rules:
            findings.extend(rule.run(graph))
        return findings

    def report(self, graph: PidGraph) -> dict:
        """Stable 'checks_run / passing / issues' summary (defensible count, §0b)."""
        findings = self.run(graph)
        # One "check" per rule per applicable node, so the denominator is stable.
        checks_run = self._applicable_checks(graph)
        issues = len(findings)
        passing = max(checks_run - issues, 0)
        return {
            "checks_run": checks_run,
            "passing": passing,
            "issues": issues,
            "findings": [f.model_dump() for f in findings],
        }

    def _applicable_checks(self, graph: PidGraph) -> int:
        from ..graph.schema import NodeType
        vessels = len(graph.nodes_of(NodeType.VESSEL))
        cvs = len(graph.nodes_of(NodeType.CONTROL_VALVE))
        tagged = len([n for n in graph.nodes if n.tag])
        # R1 (per vessel) + R4 (per vessel) + R3 (per control valve) + R2 (per tagged node)
        return vessels * 2 + cvs + tagged


def default_rules() -> list:
    return [ReliefPathRule(), DuplicateTagRule(), FailPositionRule(), LevelInstrumentRule()]


def default_engine() -> RuleEngine:
    return RuleEngine(default_rules())


def apply_fix(graph: PidGraph, fix: ProposedFix, new_revision: int | None = None) -> PidGraph:
    """Apply a ProposedFix, returning a NEW revision graph. Pure/deterministic."""
    rev = new_revision if new_revision is not None else graph.revision + 1
    g = graph.copy_as_revision(rev)

    if fix.kind == "add_subgraph":
        existing = {n.id for n in g.nodes}
        for n in fix.add_nodes:
            real = n.model_copy(deep=True)
            real.id = real.id.replace("ghost-", "")
            real.label = (real.label or "").replace(" (proposed)", "") or None
            if real.id not in existing:
                g.nodes.append(real)
                existing.add(real.id)
        for e in fix.add_edges:
            real = e.model_copy(deep=True)
            real.source = real.source.replace("ghost-", "")
            real.target = real.target.replace("ghost-", "")
            g.edges.append(real)

    elif fix.kind == "set_attr":
        for node_id, attrs in fix.set_attrs.items():
            n = g.node(node_id)
            if n:
                for k, v in attrs.items():
                    setattr(n, k, v)

    elif fix.kind == "rename":
        for node_id, new_tag in fix.rename.items():
            n = g.node(node_id)
            if n:
                n.tag = new_tag

    return g
