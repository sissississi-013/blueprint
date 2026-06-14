"""R3 — Control valve missing fail position. AMBER. Value fix -> set FC (conservative).

Bulletproof accept-fix (single attribute set). Recommended carrier for the live
"watch it fix itself" money shot (build-plan §0b): default to FC (fail-closed) and
say so on stage.
"""
from __future__ import annotations

from ..graph.schema import NodeType, PidGraph
from .base import Finding, Severity, ProposedFix

VALID_FAIL = {"FO", "FC", "FL"}


class FailPositionRule:
    id = "R3"
    requires = {"type"}

    def run(self, graph: PidGraph) -> list[Finding]:
        findings: list[Finding] = []
        for cv in graph.nodes_of(NodeType.CONTROL_VALVE):
            fp = (cv.fail_position or "").upper()
            if fp in VALID_FAIL:
                continue
            tag = cv.tag or cv.id
            findings.append(Finding(
                rule_id=self.id,
                severity=Severity.AMBER,
                node_ids=[cv.id],
                message=f"{tag} has no defined fail position (FO/FC/FL)",
                standard_ref="ISA-5.1",
                fix=ProposedFix(
                    kind="set_attr",
                    summary=f"Set {tag} fail position to FC (fail-closed, conservative)",
                    set_attrs={cv.id: {"fail_position": "FC"}},
                ),
            ))
        return findings
