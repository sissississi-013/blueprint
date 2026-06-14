# Docs — Hackathon Context Window

This folder is the shared **context window** for the Dell × NVIDIA Hackathon ("Local AI on Dell Pro Max with GB10," June 14, 2026, San Francisco). Any agent working in this repository should read these files first to understand the event, the required stack, and the strategy.

## Files

| File | What's in it |
|---|---|
| [`build-plan.md`](./build-plan.md) | **🛠️ THE BUILD PLAN — read this to start coding.** The actionable engineering plan: locked decisions, the DEXPI-vs-graphml substrate decision, tech stack + repo file tree, data contracts (graph schema, Finding JSON, WebSocket protocol, `ingest()`), the rule engine + all 6 rules with concrete logic, agent/OpenClaw/NemoClaw/OpenShell wiring + config, LLM prompt contracts, the end-to-end loop, USB checklist, hour-by-hour parallel plan, testing, fallback ladder, and definition of done. |
| [`demo-spec.md`](./demo-spec.md) | **⭐ GOVERNING SPEC (product shape).** The "P&ID Copilot": a continuous, always-on **overlay** that reads every revision engineers save in their *existing* tools and live red-lines violations (Grammarly for P&IDs). Defines the **invisibility principle** + three-layer model, the `ingest()` contract, the review-pane/graph-diff loop, rubric fit, and 5-min demo script. `build-plan.md` implements this. |
| [`build-spec.md`](./build-spec.md) | **Deep implementation reference.** Graph-first architecture, exact datasets + download commands, the concrete rule set (ISA-5.1 / API 520-521 / IEC 61511 + the 33 TU Delft rule-graph checks), exact Nemotron model IDs + serving commands. Use alongside `demo-spec.md` for the data/rules/model details it points to. |
| [`project.md`](./project.md) | Earliest framing: the "P&ID Reviewer" pitch and rubric strategy. Kept for context; superseded by `demo-spec.md` on product shape and `build-spec.md` on implementation. |
| [`hackathon-context.md`](./hackathon-context.md) | The event itself: overview, challenge, required stack, teams, prizes, rules, FAQ, logistics, and application status. Read for "what are the rules / constraints." |
| [`sponsor-tech-and-advantages.md`](./sponsor-tech-and-advantages.md) | Deep dive on the hardware (GB10), the models (Nemotron 3), and the stack (OpenClaw + NemoClaw + OpenShell), plus the "unfair advantages" to exploit. Read for "why this stack, what to leverage." |

## The One-Paragraph Summary

Build a **business/corporate AI agent that runs 100% locally** on the Dell Pro Max with GB10, using the required stack: **OpenClaw** (always-on agent framework) + **NVIDIA NemoClaw** (reference distribution) + **OpenShell** (governance-first sandbox), powered by **NVIDIA Nemotron 3** models. The winning thesis is **local + private + always-on**: zero data egress, visible governance, frontier-class models on-device with 128 GB unified memory and up to 1M-token context. Ship a working demo that runs on the box, in one day.

## What We're Building

The **P&ID Copilot**: an always-on local **overlay** that sits on top of the tools engineers already use (AutoCAD Plant 3D / SmartPlant / AVEVA), reads every P&ID revision they save, and **live red-lines safety/compliance violations** — "Grammarly underlines, but for engineering safety diagrams." Catch the missing relief valve *as it's saved*, not weeks later in HAZOP. **Invisibility principle:** nothing about their workflow changes — an `ingest()` contract swallows their real artifacts (native DEXPI / `.graphml` now; PDF and scanned image via a Nemotron vision adapter). Architecture: a **review pane** (Cytoscape.js) on the GB10 → graph-diff on each revision → a **deterministic rule engine** (NetworkX + VF2 + tag-grammar + reachability) finds violations and draws ghost-edges for what *should* exist → a local **Nemotron** model (via NemoClaw) only *narrates* and answers Q&A (never authors findings) → delta alerts over Telegram. All inside the **OpenShell** sandbox, default-deny egress, zero cloud. The wedge: P&ID *digitization and Q&A* are solved, but *continuous, invisible compliance validation* is not. See [`demo-spec.md`](./demo-spec.md) for the governing plan.

## Conventions

- These docs are **shared context**, not frozen. Keep them updated as the plan firms up.
- `project.md` is the live source of truth for the build; update it as decisions get made on the day.
