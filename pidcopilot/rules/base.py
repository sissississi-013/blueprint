"""Rule engine base types: Finding, ProposedFix, Severity, and the ISA-5.1 tag
parser util. See build-plan.md §4.2 and §5.

Core principle: the rule engine is DETERMINISTIC and produces every finding.
The LLM only narrates. A rule also returns its ProposedFix so validation and
"suggest-the-fix" are the same engine pointed in opposite directions.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Protocol

from pydantic import BaseModel, Field

from ..graph.schema import Node, Edge, PidGraph


class Severity(str, Enum):
    RED = "red"        # mandatory / safety-critical
    AMBER = "amber"    # suggested / non-blocking
    GREEN = "green"    # informational / passing


class GhostEdge(BaseModel):
    source: str
    target: Optional[str] = None        # None => target is an implied/missing node
    implied_node: Optional[Node] = None
    style: str = "ghost"


class ProposedFix(BaseModel):
    """The corrective delta — one-click acceptable. (suggest-the-fix, D8)"""
    kind: str                            # "add_subgraph" | "set_attr" | "rename"
    summary: str
    add_nodes: list[Node] = Field(default_factory=list)
    add_edges: list[Edge] = Field(default_factory=list)
    set_attrs: dict = Field(default_factory=dict)   # {node_id: {"fail_position": "FC"}}
    rename: dict = Field(default_factory=dict)       # {node_id: "PT-102"}


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    message: str
    standard_ref: str
    ghost_edges: list[GhostEdge] = Field(default_factory=list)
    matched_subgraph: list[str] = Field(default_factory=list)
    fix: Optional[ProposedFix] = None
    explanation: Optional[str] = None    # filled lazily by the LLM, on demand


class Rule(Protocol):
    id: str
    requires: set[str]                   # attrs a node must have to be checked

    def run(self, graph: PidGraph) -> list[Finding]:
        ...


# --- ISA-5.1 tag parsing (shared util; R4 needs measured_var; R6 surfaces grammar) ---

# Loosened per review: allow line-number prefix (10-) and instrument suffix (A).
TAG_RE = re.compile(r"^(?:\d+-)?([A-Z])([A-Z]*)-?(\d+)([A-Z])?$")

MEASURED_VARS = set("AFLPTSWVZCDEGHIKMNOQRU")   # permissive first-letter set
FUNCTION_LETTERS = set("IRCTYQGAVEHLDKSZ")


def normalize_tag(tag: Optional[str]) -> Optional[str]:
    if not tag:
        return None
    return tag.strip().upper().replace(" ", "")


def parse_tag(tag: Optional[str]) -> Optional[dict]:
    """Return {first, functions, loop, suffix, measured_var} or None if unparseable."""
    t = normalize_tag(tag)
    if not t:
        return None
    m = TAG_RE.match(t)
    if not m:
        return None
    first, funcs, loop, suffix = m.groups()
    return {
        "first": first,
        "functions": funcs or "",
        "loop": loop,
        "suffix": suffix or "",
        "measured_var": first,
    }


def measured_var_of(tag: Optional[str]) -> Optional[str]:
    p = parse_tag(tag)
    return p["measured_var"] if p else None
