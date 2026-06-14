"""draw.io (.drawio = mxGraph XML) -> canonical graph. DETERMINISTIC, not vision.

The live demo input surface (build-plan §6.3). Our custom stencil stores type+tag
in shape data; we read them. Falls back to deriving type from the label via the
ISA tag grammar. Handles draw.io's default base64+deflate compression of <diagram>.
"""
from __future__ import annotations

import base64
import zlib
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from ..graph.schema import Node, Edge, NodeType, EdgeKind, PidGraph
from ..rules.base import measured_var_of, parse_tag

# map a shape 'type' data attr (our stencil) -> NodeType
TYPE_MAP = {t.value: t for t in NodeType}
# map ISA first letter -> a plausible node type when only a tag is known
FIRST_LETTER_TYPE = {
    "P": NodeType.INSTRUMENT, "F": NodeType.INSTRUMENT, "L": NodeType.INSTRUMENT,
    "T": NodeType.INSTRUMENT,
}


def _maybe_inflate(xml_text: str) -> str:
    """If the file wraps a compressed <diagram>, inflate it; else return as-is."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return xml_text
    diagram = root.find(".//diagram")
    if diagram is not None and diagram.text and "<mxGraphModel" not in (diagram.text or ""):
        try:
            raw = base64.b64decode(diagram.text)
            inflated = zlib.decompress(raw, -zlib.MAX_WBITS)  # raw deflate
            return unquote(inflated.decode("utf-8"))
        except Exception:
            return xml_text
    return xml_text


def _classify(type_attr: str | None, tag: str | None, label: str | None) -> NodeType:
    if type_attr and type_attr in TYPE_MAP:
        return TYPE_MAP[type_attr]
    t = (tag or label or "")
    p = parse_tag(t)
    if p:
        first = p["first"]
        if t.upper().startswith("PSV"):
            return NodeType.PSV
        return FIRST_LETTER_TYPE.get(first, NodeType.INSTRUMENT)
    low = (label or "").lower()
    for kw, nt in (("vessel", NodeType.VESSEL), ("tank", NodeType.VESSEL),
                   ("pump", NodeType.PUMP), ("flare", NodeType.FLARE),
                   ("valve", NodeType.CONTROL_VALVE)):
        if kw in low:
            return nt
    return NodeType.UNKNOWN


def load_drawio(path: str) -> PidGraph:
    with open(path, "r", encoding="utf-8") as f:
        xml_text = _maybe_inflate(f.read())

    # find the mxGraphModel (possibly nested in <diagram>)
    root = ET.fromstring(xml_text)
    model = root if root.tag == "mxGraphModel" else root.find(".//mxGraphModel")
    if model is None:
        return PidGraph(source="drawio", nodes=[], edges=[])

    nodes: list[Node] = []
    edges: list[Edge] = []

    for cell in model.iter():
        # data attrs live on a wrapping <object> or <UserObject> with the mxCell inside
        if cell.tag in ("object", "UserObject"):
            mx = cell.find("mxCell")
            data = cell.attrib
        elif cell.tag == "mxCell":
            mx = cell
            data = cell.attrib
        else:
            continue
        if mx is None:
            continue

        cid = data.get("id") or mx.get("id")
        tag = data.get("tag") or (data.get("label") or data.get("value"))
        label = data.get("label") or data.get("value")
        type_attr = data.get("type")

        if mx.get("vertex") == "1":
            nt = _classify(type_attr, tag, label)
            fp = data.get("fail_position")
            nodes.append(Node(
                id=cid, type=nt,
                tag=(tag or None), label=(label or None),
                fail_position=(fp or None),
                measured_var=measured_var_of(tag),
                source_fidelity="rich",
            ))
        elif mx.get("edge") == "1":
            src, tgt = mx.get("source"), mx.get("target")
            if src and tgt:
                edges.append(Edge(id=cid or f"{src}-{tgt}", source=src, target=tgt,
                                  kind=EdgeKind.PROCESS))

    return PidGraph(source="drawio", nodes=nodes, edges=edges)
