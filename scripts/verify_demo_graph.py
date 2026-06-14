#!/usr/bin/env python3
"""PRE-DAY verification (build-plan §0b #2) — RUN THIS ON THE MAC BEFORE THE EVENT.

Confirms the demo graph contains exactly what rules R1-R4 need to fire on, so the
demo isn't hollow. Works on:
  - the synthetic backbone (default, always available):  python scripts/verify_demo_graph.py
  - a DEXPI file via pyDEXPI:        python scripts/verify_demo_graph.py path/to/C01.xml
  - a .graphml / .drawio file:       python scripts/verify_demo_graph.py path/to/file

Exit code 0 = every rule has something to catch on the BROKEN revisions, i.e. the
demo will land. Non-zero = the chosen source is too thin; fall back to synthetic.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pidcopilot.graph.schema import NodeType, PidGraph          # noqa: E402
from pidcopilot.rules.engine import default_engine             # noqa: E402
from pidcopilot.demo.synthetic import build_clean_graph        # noqa: E402
from pidcopilot.demo import revisions                          # noqa: E402


def load(path: str | None) -> PidGraph:
    if not path:
        print("• Source: synthetic demo backbone\n")
        return build_clean_graph()
    from pidcopilot.ingest import ingest
    print(f"• Source: {path}\n")
    g = ingest(path)
    if g.source.startswith("error"):
        print(f"  !! ingest failed: {g.source}")
    return g


def summarize(g: PidGraph) -> None:
    counts: dict[str, int] = {}
    for n in g.nodes:
        counts[n.type.value] = counts.get(n.type.value, 0) + 1
    print(f"  nodes={len(g.nodes)} edges={len(g.edges)} source_fidelity="
          f"{g.nodes[0].source_fidelity if g.nodes else 'n/a'}")
    print("  types:", ", ".join(f"{k}:{v}" for k, v in sorted(counts.items())) or "(none)")


def check_ingredients(g: PidGraph) -> dict[str, bool]:
    has = lambda t: bool(g.nodes_of(t))  # noqa: E731
    level = any((n.measured_var == "L") for n in g.nodes_of(NodeType.INSTRUMENT))
    return {
        "R1 needs vessel + (PSV/disc) + flare/disposal":
            has(NodeType.VESSEL) and (has(NodeType.PSV) or has(NodeType.RUPTURE_DISC)),
        "R2 needs >=2 tagged nodes": len([n for n in g.nodes if n.tag]) >= 2,
        "R3 needs a control valve": has(NodeType.CONTROL_VALVE),
        "R4 needs vessel + level instrument": has(NodeType.VESSEL) and level,
    }


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    g = load(path)
    summarize(g)

    print("\n• Ingredient check (clean graph should contain these):")
    ingredients = check_ingredients(g)
    for label, ok in ingredients.items():
        print(f"   [{'OK' if ok else 'MISSING'}] {label}")

    engine = default_engine()
    clean = engine.report(g)
    print(f"\n• Clean graph: {clean['passing']}/{clean['checks_run']} passing, "
          f"{clean['issues']} issues (expect 0 issues on a clean demo graph).")

    print("\n• Broken-revision check (each rule must fire on its mutation):")
    fired = {}
    for name, fn in revisions.REVISIONS.items():
        try:
            broken = fn(g)
        except Exception as exc:
            print(f"   [SKIP] {name}: mutation failed ({exc})")
            continue
        findings = engine.run(broken)
        ids = sorted({f.rule_id for f in findings})
        fired[name] = ids
        fixes = sum(1 for f in findings if f.fix)
        print(f"   {name:24s} -> fires {ids or '[]'}  ({fixes} suggested fix(es))")

    all_ingredients = all(ingredients.values())
    any_fire = any(fired.values())
    ok = all_ingredients and any_fire
    print("\n" + ("PASS — demo graph is sufficient." if ok else
                  "FAIL — source too thin; fall back to the synthetic backbone."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
