"""Synthetic demo P&ID — the DEMO BACKBONE (build-plan §0b #2).

Hand-built so it contains EXACTLY what R1-R4 need, so the demo never depends on
pyDEXPI parsing C01. The clean graph passes all four rules; demo/revisions.py
mutates it to trigger each finding live.

Clean topology:
    INLET -> V-101(vessel) -> FV-101(control valve, FC) -> OUTLET
    V-101 -> PSV-101(psv) -> F-1(flare)        [relief path: satisfies R1]
    V-101 -- LIT-101(level instrument)          [satisfies R4]
    tags unique                                  [satisfies R2]
    FV-101 has fail_position=FC                   [satisfies R3]
"""
from __future__ import annotations

from ..graph.schema import Node, Edge, NodeType, EdgeKind, PidGraph


def build_clean_graph() -> PidGraph:
    nodes = [
        Node(id="IN-1", type=NodeType.INLET, tag="IN-1", label="Feed inlet"),
        Node(id="V-101", type=NodeType.VESSEL, tag="V-101", label="Separator"),
        Node(id="FV-101", type=NodeType.CONTROL_VALVE, tag="FV-101",
             label="Flow control valve", fail_position="FC", measured_var="F"),
        Node(id="OUT-1", type=NodeType.OUTLET, tag="OUT-1", label="Product outlet"),
        Node(id="PSV-101", type=NodeType.PSV, tag="PSV-101", label="Relief valve"),
        Node(id="F-1", type=NodeType.FLARE, tag="F-1", label="Flare header"),
        Node(id="LIT-101", type=NodeType.INSTRUMENT, tag="LIT-101",
             label="Level transmitter", measured_var="L"),
    ]
    edges = [
        Edge(id="e1", source="IN-1", target="V-101"),
        Edge(id="e2", source="V-101", target="FV-101"),
        Edge(id="e3", source="FV-101", target="OUT-1"),
        Edge(id="e4", source="V-101", target="PSV-101"),
        Edge(id="e5", source="PSV-101", target="F-1"),
        Edge(id="e6", source="V-101", target="LIT-101", kind=EdgeKind.INSTRUMENT),
    ]
    return PidGraph(revision=1, source="synthetic", nodes=nodes, edges=edges)
