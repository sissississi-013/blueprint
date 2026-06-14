"""Thin local-inference client (NemoClaw -> Nemotron via Ollama).

The LLM NEVER authors findings (build-plan §9). `narrate` explains a finding the
rule engine already produced; `answer` phrases a result the server already
computed deterministically. Both degrade gracefully to the rule-engine text if
no model is reachable, so the demo's red-lines never depend on inference.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx

from .. import config


def _generate(prompt: str, model: str | None = None, timeout: float = 60.0) -> str:
    model = model or config.NEMOTRON_MODEL
    try:
        r = httpx.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception:
        return ""   # caller falls back to deterministic text


def narrate(finding: dict, context: str = "") -> str:
    """Explain one finding. Falls back to the deterministic message if no model."""
    prompt = (
        "You are a P&ID safety reviewer. Explain the following finding in 2-3 "
        "sentences: what is wrong, why it matters, and the standard. Do NOT add, "
        "remove, or contradict findings. Do NOT claim anything passes.\n\n"
        f"FINDING: {finding.get('message')} (standard: {finding.get('standard_ref')})\n"
        f"CONTEXT: {context}\n"
    )
    out = _generate(prompt)
    if out:
        return out
    return (f"{finding.get('message')}. This violates {finding.get('standard_ref')}. "
            f"Recommended: {(finding.get('fix') or {}).get('summary', 'review with an engineer')}.")


def answer(question: str, computed_result: str) -> str:
    """Phrase a deterministically-computed result. Never computes the answer itself."""
    prompt = (
        "Phrase the following computed result as a one-sentence answer to the "
        "question. Do not add facts.\n"
        f"QUESTION: {question}\nRESULT: {computed_result}\n"
    )
    out = _generate(prompt)
    return out or computed_result


def vision_extract(image_path: str, prompt: str,
                   model: str | None = None, timeout: float = 120.0) -> str:
    """Send image BYTES + prompt to the VL model; return its raw text.

    Unlike narration, this is load-bearing: the bytes actually go over the wire,
    so the model's output drives the graph. Set config.VISION_MOCK to a file of
    canned JSON to exercise the whole pipeline with no model (pre-staging / CI).
    Exceptions propagate; ingest/base.py wraps adapters and the vision adapter
    falls back to a frozen fixture, so a dead model never crashes the loop.
    """
    if config.VISION_MOCK:
        return Path(config.VISION_MOCK).read_text()
    model = model or config.VL_MODEL
    data, mime = _image_bytes(image_path)
    b64 = base64.b64encode(data).decode("ascii")
    if config.VISION_BACKEND == "vllm":
        return _vision_vllm(b64, mime, prompt, model, timeout)
    return _vision_ollama(b64, prompt, model, timeout)


def _vision_ollama(b64: str, prompt: str, model: str, timeout: float) -> str:
    r = httpx.post(
        f"{config.OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "images": [b64], "stream": False},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("response", "").strip()


def _vision_vllm(b64: str, mime: str, prompt: str, model: str, timeout: float) -> str:
    r = httpx.post(
        f"{config.VLLM_URL}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _image_bytes(image_path: str) -> tuple[bytes, str]:
    """Load an image as model-ready (bytes, mime_type).

    PDFs are rasterized (first page) via PyMuPDF; large rasters are downscaled via
    Pillow. Both libs are optional (Python 3.14 wheel risk): without Pillow a
    raster is sent full-size; without PyMuPDF a PDF raises and the vision adapter
    falls back to its frozen fixture.
    """
    p = Path(image_path)
    if p.suffix.lower() == ".pdf":
        return _pdf_first_page_png(image_path), "image/png"
    return _maybe_downscale(p.read_bytes(), p.suffix.lower())


def _pdf_first_page_png(image_path: str) -> bytes:
    import fitz  # PyMuPDF, optional
    doc = fitz.open(image_path)
    page = doc.load_page(0)
    scale = config.VISION_MAX_EDGE / max(page.rect.width, page.rect.height, 1)
    matrix = fitz.Matrix(scale, scale) if scale < 1 else fitz.Matrix(1, 1)
    return page.get_pixmap(matrix=matrix).tobytes("png")


def _maybe_downscale(data: bytes, suffix: str) -> tuple[bytes, str]:
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
    try:
        from PIL import Image  # optional
    except ImportError:
        return data, mime
    img = Image.open(io.BytesIO(data))
    if max(img.size) <= config.VISION_MAX_EDGE:
        return data, mime
    scale = config.VISION_MAX_EDGE / max(img.size)
    img = img.resize((int(img.width * scale), int(img.height * scale)))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue(), "image/png"
