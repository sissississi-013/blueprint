"""DEXPI .xml (Proteus) -> canonical graph via pyDEXPI. PRIMARY rule-bearing source.

IMPORTANT (open-unknown #1): pyDEXPI's exact API names must be confirmed on-site
against the installed version. This adapter is written defensively: it tries the
likely entrypoints and, failing that, raises a clear message so we fall back to
the synthetic demo graph (which is the actual demo backbone). Do NOT let this
block the build.
"""
from __future__ import annotations

from ..graph.schema import Node, Edge, NodeType, EdgeKind, PidGraph

# DEXPI class name (substring, lowercased) -> NodeType. Extend on-site once the
# real class names are known.
DEXPI_TYPE_HINTS = [
    ("safetyvalve", NodeType.PSV), ("reliefvalve", NodeType.PSV),
    ("rupturedisc", NodeType.RUPTURE_DISC),
    ("controlvalve", NodeType.CONTROL_VALVE),
    ("checkvalve", NodeType.CHECK_VALVE),
    ("ballvalve", NodeType.BLOCK_VALVE), ("gatevalve", NodeType.BLOCK_VALVE),
    ("globevalve", NodeType.CONTROL_VALVE),
    ("strainer", NodeType.STRAINER), ("filter", NodeType.STRAINER),
    ("vessel", NodeType.VESSEL), ("tank", NodeType.VESSEL), ("drum", NodeType.VESSEL),
    ("column", NodeType.VESSEL),
    ("pump", NodeType.PUMP), ("compressor", NodeType.COMPRESSOR),
    ("flare", NodeType.FLARE),
    ("instrument", NodeType.INSTRUMENT), ("transmitter", NodeType.INSTRUMENT),
]


def _classify(class_name: str) -> NodeType:
    low = (class_name or "").lower()
    for sub, nt in DEXPI_TYPE_HINTS:
        if sub in low:
            return nt
    return NodeType.UNKNOWN


def load_dexpi(path: str) -> PidGraph:
    try:
        import pydexpi  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "pyDEXPI not installed. `pip install git+https://github.com/"
            "process-intelligence-research/pyDEXPI`. Until then, use the synthetic "
            "demo graph (pidcopilot.demo.synthetic)."
        ) from exc

    # --- Best-effort: confirm these names against the installed pyDEXPI on-site. ---
    model = _parse_proteus(path)
    nxg = _to_networkx(model)

    nodes: list[Node] = []
    for nid, attrs in nxg.nodes(data=True):
        class_name = str(attrs.get("dexpi_class", attrs.get("class", "")))
        tag = attrs.get("tag") or attrs.get("TagName") or attrs.get("label")
        fp = attrs.get("failAction") or attrs.get("fail_position")
        from ..rules.base import measured_var_of
        nodes.append(Node(
            id=str(nid), type=_classify(class_name), tag=tag,
            label=tag or class_name or None,
            fail_position=_norm_fail(fp),
            measured_var=measured_var_of(tag),
            attrs={"dexpi_class": class_name},
            source_fidelity="rich",
        ))
    edges: list[Edge] = []
    for i, (s, t, attrs) in enumerate(nxg.edges(data=True)):
        edges.append(Edge(id=f"e{i}", source=str(s), target=str(t),
                          kind=EdgeKind.PROCESS))
    return PidGraph(source="dexpi", nodes=nodes, edges=edges)


def _parse_proteus(path: str):
    """Try known pyDEXPI Proteus loader entrypoints. CONFIRM ON-SITE."""
    import importlib
    candidates = [
        ("pydexpi.loaders.proteus_serializer", "ProteusSerializer"),
        ("pydexpi.loaders.proteus", "parse"),
        ("pydexpi.loaders", "load_proteus"),
    ]
    for mod_name, attr in candidates:
        try:
            mod = importlib.import_module(mod_name)
            obj = getattr(mod, attr)
            return obj(path) if callable(obj) else obj
        except (ImportError, AttributeError):
            continue
    raise RuntimeError("Could not locate pyDEXPI Proteus loader — confirm API on-site.")


def _to_networkx(model):
    """Try known pyDEXPI -> networkx exporters. CONFIRM ON-SITE."""
    import importlib
    candidates = [
        ("pydexpi.toolkits.nx_export", "to_networkx"),
        ("pydexpi.toolkits.graph", "model_to_graph"),
    ]
    for mod_name, attr in candidates:
        try:
            mod = importlib.import_module(mod_name)
            return getattr(mod, attr)(model)
        except (ImportError, AttributeError):
            continue
    # some versions expose .to_networkx() on the model
    if hasattr(model, "to_networkx"):
        return model.to_networkx()
    raise RuntimeError("Could not locate pyDEXPI networkx exporter — confirm API on-site.")


def _norm_fail(fp):
    if not fp:
        return None
    s = str(fp).lower()
    if "open" in s:
        return "FO"
    if "close" in s:
        return "FC"
    if "last" in s or "lock" in s:
        return "FL"
    return None
