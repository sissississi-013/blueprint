"""ingest() dispatcher — one interface, several adapters, one canonical graph.

Routes by extension. Adapters never raise into the loop: on failure they return
an empty graph (the server surfaces an error annotation). See build-plan §4.4/§6.
"""
from __future__ import annotations

import os

from ..graph.schema import PidGraph


def ingest(path: str, hint: str | None = None) -> PidGraph:
    ext = (hint or os.path.splitext(path)[1].lower().lstrip(".")).lower()
    try:
        if ext in ("xml", "dexpi"):
            from .dexpi_adapter import load_dexpi
            return load_dexpi(path)
        if ext == "graphml":
            from .graphml_adapter import load_graphml
            return load_graphml(path)
        if ext in ("drawio", "mxgraph"):
            from .drawio_adapter import load_drawio
            return load_drawio(path)
        if ext in ("pdf", "png", "jpg", "jpeg"):
            from .vision_adapter import load_vision
            return load_vision(path)
    except Exception as exc:  # never crash the loop
        return PidGraph(source="error", nodes=[], edges=[],
                        ).model_copy(update={"source": f"error:{ext}:{exc}"})
    # default: try drawio xml (it's the live surface)
    from .drawio_adapter import load_drawio
    return load_drawio(path)
