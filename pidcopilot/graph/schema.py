"""Canonical graph schema — the single representation every adapter targets,
every rule reads, and the pane renders. See build-plan.md §4.1.

Design note: adapters with rich semantics (DEXPI, synthetic, draw.io stencil)
populate tags/types/fail_position fully (source_fidelity="rich"). Topology-only
sources (PID2Graph .graphml) leave rule-required attrs None
(source_fidelity="topology"); rules self-skip nodes lacking what they require, so
they never false-flag on a coarse graph.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

import networkx as nx
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    VESSEL = "vessel"
    PUMP = "pump"
    COMPRESSOR = "compressor"
    CONTROL_VALVE = "control_valve"
    BLOCK_VALVE = "block_valve"
    CHECK_VALVE = "check_valve"
    PSV = "psv"                # pressure safety/relief valve
    RUPTURE_DISC = "rupture_disc"
    STRAINER = "strainer"
    INSTRUMENT = "instrument"
    FLARE = "flare"
    DISPOSAL = "disposal"
    INLET = "inlet"
    OUTLET = "outlet"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class EdgeKind(str, Enum):
    PROCESS = "process"
    SIGNAL = "signal"
    INSTRUMENT = "instrument"


class Node(BaseModel):
    id: str
    type: NodeType = NodeType.UNKNOWN
    tag: Optional[str] = None
    label: Optional[str] = None
    fail_position: Optional[str] = None      # "FO" | "FC" | "FL" (control valves)
    measured_var: Optional[str] = None       # ISA first-letter, derived from tag
    bbox: Optional[tuple[float, float, float, float]] = None
    attrs: dict = Field(default_factory=dict)
    source_fidelity: str = "rich"            # "rich" | "topology"


class Edge(BaseModel):
    id: str
    source: str
    target: str
    kind: EdgeKind = EdgeKind.PROCESS
    directed: bool = True
    attrs: dict = Field(default_factory=dict)


class PidGraph(BaseModel):
    """A revision of a P&ID as a canonical graph."""
    revision: int = 0
    source: str = "synthetic"                # "dexpi" | "graphml" | "drawio" | "vision" | "synthetic"
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    # --- convenience accessors -------------------------------------------------
    def node(self, node_id: str) -> Optional[Node]:
        return next((n for n in self.nodes if n.id == node_id), None)

    def nodes_of(self, *types: NodeType) -> list[Node]:
        s = set(types)
        return [n for n in self.nodes if n.type in s]

    def to_nx(self) -> nx.DiGraph:
        """Build a networkx DiGraph with the Node/Edge objects attached as 'data'."""
        g = nx.DiGraph()
        for n in self.nodes:
            g.add_node(n.id, data=n, type=n.type.value, tag=n.tag,
                       measured_var=n.measured_var)
        for e in self.edges:
            g.add_edge(e.source, e.target, data=e, kind=e.kind.value, id=e.id)
        return g

    def copy_as_revision(self, revision: int) -> "PidGraph":
        return PidGraph(
            revision=revision,
            source=self.source,
            nodes=[n.model_copy(deep=True) for n in self.nodes],
            edges=[e.model_copy(deep=True) for e in self.edges],
        )
