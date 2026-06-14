"""Scripted "engineer saved a revision" mutations for the demo.

Each maps to a pane button / a file dropped in the watched folder. Deterministic
and rehearsable — they own the demo beat (build-plan §7).
"""
from __future__ import annotations

from ..graph.schema import PidGraph


def delete_psv_101(g: PidGraph) -> PidGraph:
    """Triggers R1 (missing relief path) — the scary lead finding."""
    out = g.copy_as_revision(g.revision + 1)
    out.nodes = [n for n in out.nodes if n.id != "PSV-101"]
    out.edges = [e for e in out.edges if "PSV-101" not in (e.source, e.target)]
    return out


def strip_fail_position(g: PidGraph) -> PidGraph:
    """Triggers R3 (missing fail position) — the bulletproof accept-fix money shot."""
    out = g.copy_as_revision(g.revision + 1)
    cv = out.node("FV-101")
    if cv:
        cv.fail_position = None
    return out


def duplicate_tag(g: PidGraph) -> PidGraph:
    """Triggers R2 (duplicate tag) — value-fix money shot alternative."""
    out = g.copy_as_revision(g.revision + 1)
    lit = out.node("LIT-101")
    if lit:
        lit.tag = "FV-101"   # collide with the control valve's tag
    return out


def delete_level_instrument(g: PidGraph) -> PidGraph:
    """Triggers R4 (missing level instrument)."""
    out = g.copy_as_revision(g.revision + 1)
    out.nodes = [n for n in out.nodes if n.id != "LIT-101"]
    out.edges = [e for e in out.edges if "LIT-101" not in (e.source, e.target)]
    return out


REVISIONS = {
    "delete_psv_101": delete_psv_101,
    "strip_fail_position": strip_fail_position,
    "duplicate_tag": duplicate_tag,
    "delete_level_instrument": delete_level_instrument,
}


def apply_named_revision(name: str, g: PidGraph) -> PidGraph:
    fn = REVISIONS.get(name)
    if not fn:
        raise KeyError(f"unknown revision '{name}'. Options: {list(REVISIONS)}")
    return fn(g)
