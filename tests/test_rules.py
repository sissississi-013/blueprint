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
