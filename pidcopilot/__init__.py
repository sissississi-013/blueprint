"""P&ID Copilot — local, always-on engineering-diagram validation agent.

The deterministic core (graph + rules) lives here. The LLM (Nemotron via
NemoClaw) only narrates findings; it never authors them. See docs/build-plan.md.
"""

__version__ = "0.1.0"
