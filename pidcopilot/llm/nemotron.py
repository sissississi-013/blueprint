"""Thin local-inference client (NemoClaw -> Nemotron via Ollama).

The LLM NEVER authors findings (build-plan §9). `narrate` explains a finding the
rule engine already produced; `answer` phrases a result the server already
computed deterministically. Both degrade gracefully to the rule-engine text if
no model is reachable, so the demo's red-lines never depend on inference.
"""
from __future__ import annotations

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


def vision_extract(image_path: str, prompt: str) -> str:
    """Stub for the VL adapter; wire to the running VL model on-site."""
    return _generate(f"[image:{image_path}]\n{prompt}", model=config.VL_MODEL, timeout=120.0)
