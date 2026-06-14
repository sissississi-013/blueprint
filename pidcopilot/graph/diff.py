"""Revision diff — kept ONLY for regression messaging (build-plan §0b).

We deliberately do NOT use diff to scope validation: at 30-200 nodes a full
re-scan is microseconds, so diff-as-scoping is bug surface for zero benefit.
This module answers "what changed between revisions?" for the alert text
(e.g. "PSV-101 was present last revision and is now gone").
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .schema import PidGraph


@dataclass
class GraphDiff:
    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    added_edges: list[str] = field(default_factory=list)
    removed_edges: list[str] = field(default_factory=list)
    changed_attrs: list[str] = field(default_factory=list)   # node ids with attr changes

    def is_empty(self) -> bool:
        return not (self.added_nodes or self.removed_nodes or self.added_edges
                    or self.removed_edges or self.changed_attrs)


def _label(g: PidGraph, node_id: str) -> str:
    n = g.node(node_id)
    return (n.tag or n.label or node_id) if n else node_id


def diff_graphs(old: PidGraph, new: PidGraph) -> GraphDiff:
    old_nodes = {n.id: n for n in old.nodes}
    new_nodes = {n.id: n for n in new.nodes}
    old_edges = {e.id for e in old.edges}
    new_edges = {e.id for e in new.edges}

    d = GraphDiff(
        added_nodes=[i for i in new_nodes if i not in old_nodes],
        removed_nodes=[i for i in old_nodes if i not in new_nodes],
        added_edges=[i for i in new_edges if i not in old_edges],
        removed_edges=[i for i in old_edges if i not in new_edges],
    )
    for nid in set(old_nodes) & set(new_nodes):
        o, n = old_nodes[nid], new_nodes[nid]
        if (o.tag, o.type, o.fail_position) != (n.tag, n.type, n.fail_position):
            d.changed_attrs.append(nid)
    return d


def regression_messages(old: PidGraph, new: PidGraph) -> list[str]:
    """Human-readable 'over time' messages for the Telegram/local alert feed."""
    d = diff_graphs(old, new)
    msgs: list[str] = []
    for nid in d.removed_nodes:
        msgs.append(f"{_label(old, nid)} was present in rev {old.revision} and is now gone")
    for nid in d.changed_attrs:
        msgs.append(f"{_label(new, nid)} changed between rev {old.revision} and {new.revision}")
    return msgs
