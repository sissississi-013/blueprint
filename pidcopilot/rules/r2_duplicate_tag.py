"""R2 — Duplicate instrument tag. RED. Value fix -> rename to next free loop number.

This is a reliable, bulletproof accept-fix (no graph surgery) — a good candidate
to carry the live "watch it fix itself" beat (build-plan §0b).
"""
from __future__ import annotations

from collections import defaultdict

from ..graph.schema import PidGraph
from .base import Finding, Severity, ProposedFix, normalize_tag, parse_tag


class DuplicateTagRule:
    id = "R2"
    requires = {"tag"}

    def run(self, graph: PidGraph) -> list[Finding]:
        groups: dict[str, list[str]] = defaultdict(list)
        for n in graph.nodes:
            t = normalize_tag(n.tag)
            if t:
                groups[t].append(n.id)

        findings: list[Finding] = []
        for tag, ids in groups.items():
            if len(ids) < 2:
                continue
            # propose renaming all but the first to free loop numbers.
            dup_id = ids[1]
            new_tag = _next_free_tag(graph, tag)
            findings.append(Finding(
                rule_id=self.id,
                severity=Severity.RED,
                node_ids=ids,
                matched_subgraph=ids,
                message=f"Duplicate tag {tag} on {len(ids)} components",
                standard_ref="ISA-5.1",
                fix=ProposedFix(
                    kind="rename",
                    summary=f"Rename one {tag} to {new_tag}",
                    rename={dup_id: new_tag},
                ),
            ))
        return findings


def _next_free_tag(graph: PidGraph, tag: str) -> str:
    p = parse_tag(tag)
    used = {normalize_tag(n.tag) for n in graph.nodes if n.tag}
    if not p:
        # fall back to suffixing
        i = 2
        while f"{tag}-{i}" in used:
            i += 1
        return f"{tag}-{i}"
    prefix = f"{p['first']}{p['functions']}"
    loop = int(p["loop"])
    while f"{prefix}-{loop}" in used:
        loop += 1
    return f"{prefix}-{loop}"
