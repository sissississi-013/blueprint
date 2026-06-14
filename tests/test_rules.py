"""Rule unit tests on tiny hand-built graphs + the synthetic backbone.

These are the safety net (build-plan §13): they let us refactor fast and assert
the demo beats actually fire. Run: pytest -q
"""
from pidcopilot.graph.schema import Node, Edge, NodeType, EdgeKind, PidGraph
from pidcopilot.rules.engine import default_engine, apply_fix
from pidcopilot.demo.synthetic import build_clean_graph
from pidcopilot.demo import revisions


def _ids(findings):
    return sorted({f.rule_id for f in findings})


def test_clean_graph_passes_all_four():
    g = build_clean_graph()
    findings = default_engine().run(g)
    assert findings == [], f"clean graph should have no findings, got {_ids(findings)}"


def test_delete_psv_triggers_r1_with_fix():
    g = revisions.delete_psv_101(build_clean_graph())
    findings = default_engine().run(g)
    r1 = [f for f in findings if f.rule_id == "R1"]
    assert r1, "R1 should fire when the PSV is removed"
    assert r1[0].fix and r1[0].fix.kind == "add_subgraph"
    assert r1[0].ghost_edges, "R1 should emit a ghost edge"


def test_accept_r1_fix_clears_it():
    g = revisions.delete_psv_101(build_clean_graph())
    eng = default_engine()
    r1 = next(f for f in eng.run(g) if f.rule_id == "R1")
    fixed = apply_fix(g, r1.fix)
    assert not [f for f in eng.run(fixed) if f.rule_id == "R1"], "fix should clear R1"


def test_strip_fail_position_triggers_r3_and_fixes_to_fc():
    g = revisions.strip_fail_position(build_clean_graph())
    eng = default_engine()
    r3 = next(f for f in eng.run(g) if f.rule_id == "R3")
    assert r3.fix.set_attrs["FV-101"]["fail_position"] == "FC"
    fixed = apply_fix(g, r3.fix)
    assert not [f for f in eng.run(fixed) if f.rule_id == "R3"]


def test_duplicate_tag_triggers_r2_and_rename_fix():
    g = revisions.duplicate_tag(build_clean_graph())
    eng = default_engine()
    r2 = next(f for f in eng.run(g) if f.rule_id == "R2")
    assert r2.fix.kind == "rename"
    fixed = apply_fix(g, r2.fix)
    assert not [f for f in eng.run(fixed) if f.rule_id == "R2"]


def test_delete_level_instrument_triggers_r4():
    g = revisions.delete_level_instrument(build_clean_graph())
    findings = default_engine().run(g)
    assert "R4" in _ids(findings)


def test_r1_no_flare_does_not_crash():
    # vessel with no relief and no disposal: R1 must imply a flare, not throw.
    g = PidGraph(nodes=[Node(id="V-1", type=NodeType.VESSEL, tag="V-1")], edges=[])
    findings = default_engine().run(g)
    r1 = next(f for f in findings if f.rule_id == "R1")
    assert r1.fix and len(r1.fix.add_nodes) >= 2  # PSV + implied flare


def test_topology_only_nodes_self_skip_tag_rules():
    # graphml-style nodes (no tag) must not false-flag R2/R3.
    g = PidGraph(nodes=[
        Node(id="a", type=NodeType.VESSEL, source_fidelity="topology"),
        Node(id="b", type=NodeType.CONTROL_VALVE, source_fidelity="topology"),
    ], edges=[])
    findings = default_engine().run(g)
    # R3 fires (control valve genuinely lacks fail position) but R2 must not (no tags)
    assert "R2" not in _ids(findings)


def _r1_ids(findings):
    return {nid for f in findings if f.rule_id == "R1" for nid in f.node_ids}


def test_r1_flags_vessel_whose_only_psv_belongs_to_another_vessel():
    # Two vessels share an inlet header. V-101 has a relief path; V-202 has none.
    # On an undirected whole-component graph, V-202 would reach PSV-101 via the
    # shared header and be wrongly cleared. R1 must be per-vessel directed.
    g = PidGraph(nodes=[
        Node(id="IN-1", type=NodeType.INLET, tag="IN-1"),
        Node(id="V-101", type=NodeType.VESSEL, tag="V-101"),
        Node(id="V-202", type=NodeType.VESSEL, tag="V-202"),
        Node(id="PSV-101", type=NodeType.PSV, tag="PSV-101"),
        Node(id="F-1", type=NodeType.FLARE, tag="F-1"),
        Node(id="OUT-2", type=NodeType.OUTLET, tag="OUT-2"),
    ], edges=[
        Edge(id="e1", source="IN-1", target="V-101"),
        Edge(id="e2", source="IN-1", target="V-202"),
        Edge(id="e3", source="V-101", target="PSV-101"),
        Edge(id="e4", source="PSV-101", target="F-1"),
        Edge(id="e5", source="V-202", target="OUT-2"),
    ])
    flagged = _r1_ids(default_engine().run(g))
    assert "V-202" in flagged, "V-202 has no relief path of its own and must flag"
    assert "V-101" not in flagged, "V-101 is genuinely protected and must not flag"


def test_r1_does_not_count_relief_reached_only_through_signal_line():
    # The PSV is reachable only across an INSTRUMENT edge (a signal line, not a
    # pipe). Relief routing is physical: a signal line is not a relief path.
    g = PidGraph(nodes=[
        Node(id="V-300", type=NodeType.VESSEL, tag="V-300"),
        Node(id="PSV-300", type=NodeType.PSV, tag="PSV-300"),
        Node(id="F-3", type=NodeType.FLARE, tag="F-3"),
    ], edges=[
        Edge(id="s1", source="V-300", target="PSV-300", kind=EdgeKind.INSTRUMENT),
        Edge(id="p1", source="PSV-300", target="F-3", kind=EdgeKind.PROCESS),
    ])
    flagged = _r1_ids(default_engine().run(g))
    assert "V-300" in flagged, "relief over a signal line is not a real relief path"


def test_vision_mock_pipeline_builds_graph_and_fires_rules(tmp_path, monkeypatch):
    # With VISION_MOCK set, the whole vision pipeline runs with no model:
    # canned VLM JSON -> coerce -> canonical graph -> rule engine.
    from pidcopilot import config
    from pidcopilot.ingest.vision_adapter import load_vision

    mock = tmp_path / "vlm.json"
    mock.write_text(
        "```json\n"
        '{"symbols":['
        '{"id":"n1","type":"vessel","tag":"V-101"},'
        '{"id":"n2","type":"instrument","tag":"PT-101"},'
        '{"id":"n3","type":"instrument","tag":"PT-101"}],'
        '"lines":[{"source":"n1","target":"n2"}]}\n'
        "```\n"
    )
    monkeypatch.setattr(config, "VISION_MOCK", str(mock))
    g = load_vision("nonexistent.png")
    assert len(g.nodes) == 3 and g.source == "vision"
    # duplicate PT-101 -> R2 must fire on a graph that came purely from "vision".
    assert "R2" in _ids(default_engine().run(g))


def test_r1_ignores_edge_direction_through_a_valve():
    # Relief path drawn with the vessel<->valve segment reversed (common in
    # hand-drawn exports). A control/block valve imposes no flow direction, so the
    # vessel is still protected (build-plan R1: "ignoring direction through valves").
    g = PidGraph(nodes=[
        Node(id="V-400", type=NodeType.VESSEL, tag="V-400"),
        Node(id="BV-400", type=NodeType.BLOCK_VALVE, tag="BV-400"),
        Node(id="PSV-400", type=NodeType.PSV, tag="PSV-400"),
        Node(id="F-4", type=NodeType.FLARE, tag="F-4"),
    ], edges=[
        Edge(id="e1", source="BV-400", target="V-400"),   # drawn backwards
        Edge(id="e2", source="BV-400", target="PSV-400"),
        Edge(id="e3", source="PSV-400", target="F-4"),
    ])
    assert "V-400" not in _r1_ids(default_engine().run(g))


def test_r1_mints_distinct_psv_tags_for_multiple_unprotected_vessels():
    # Two unprotected vessels must get DISTINCT proposed PSVs; otherwise accepting
    # both fixes collapses to one shared PSV (apply_fix dedupes add_nodes by id).
    g = PidGraph(nodes=[
        Node(id="V-1", type=NodeType.VESSEL, tag="V-1"),
        Node(id="V-2", type=NodeType.VESSEL, tag="V-2"),
    ], edges=[])
    r1 = [f for f in default_engine().run(g) if f.rule_id == "R1"]
    assert len(r1) == 2
    psvs = {n.tag for f in r1 for n in f.fix.add_nodes if n.type == NodeType.PSV}
    assert len(psvs) == 2, f"each vessel needs its own PSV tag, got {psvs}"
