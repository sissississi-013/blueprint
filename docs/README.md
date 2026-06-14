# Docs — Hackathon Context Window

This folder is the shared **context window** for the Dell × NVIDIA Hackathon ("Local AI on Dell Pro Max with GB10," June 14, 2026, San Francisco). Any agent working in this repository should read these files first to understand the event, the required stack, and the strategy.

## Files

| File | What's in it |
|---|---|
| [`demo-spec.md`](./demo-spec.md) | **⭐ NEWEST / GOVERNING SPEC — start here.** The "P&ID Copilot": a continuous, always-on copilot that live red-lines violations on the diagram *as the engineer edits* (Grammarly for P&IDs). Live Cytoscape.js canvas + graph-diff loop + ghost-edges, explicit rubric fit, 5-min demo script, and load-bearing OpenClaw/NemoClaw/OpenShell usage. Defines **product shape**. |
| [`build-spec.md`](./build-spec.md) | **Deep implementation reference.** Graph-first architecture, exact datasets + download commands, the concrete rule set (ISA-5.1 / API 520-521 / IEC 61511 + the 33 TU Delft rule-graph checks), exact Nemotron model IDs + serving commands. Use alongside `demo-spec.md` for the data/rules/model details it points to. |
| [`project.md`](./project.md) | Earliest framing: the "P&ID Reviewer" pitch and rubric strategy. Kept for context; superseded by `demo-spec.md` on product shape and `build-spec.md` on implementation. |
| [`hackathon-context.md`](./hackathon-context.md) | The event itself: overview, challenge, required stack, teams, prizes, rules, FAQ, logistics, and application status. Read for "what are the rules / constraints." |
| [`sponsor-tech-and-advantages.md`](./sponsor-tech-and-advantages.md) | Deep dive on the hardware (GB10), the models (Nemotron 3), and the stack (OpenClaw + NemoClaw + OpenShell), plus the "unfair advantages" to exploit. Read for "why this stack, what to leverage." |

## The One-Paragraph Summary

Build a **business/corporate AI agent that runs 100% locally** on the Dell Pro Max with GB10, using the required stack: **OpenClaw** (always-on agent framework) + **NVIDIA NemoClaw** (reference distribution) + **OpenShell** (governance-first sandbox), powered by **NVIDIA Nemotron 3** models. The winning thesis is **local + private + always-on**: zero data egress, visible governance, frontier-class models on-device with 128 GB unified memory and up to 1M-token context. Ship a working demo that runs on the box, in one day.

## What We're Building

The **P&ID Copilot**: an always-on local agent that **watches an engineer edit a P&ID and live red-lines safety/compliance violations on the drawing in real time** — "Grammarly underlines, but for engineering safety diagrams." Catch the missing relief valve *as it's deleted*, not weeks later in HAZOP. Architecture: a live **Cytoscape.js graph canvas** on the GB10 emits `graph-changed` events → a **deterministic rule engine** (NetworkX + VF2 + tag-grammar + reachability) finds violations and draws ghost-edges for what *should* exist → a local **Nemotron** model (via NemoClaw) only *narrates* findings and answers Q&A (never authors them) → delta alerts over Telegram. Everything inside the **OpenShell** sandbox, default-deny egress, zero cloud. The wedge: P&ID *digitization and Q&A* are solved, but *continuous, automated compliance validation* is not. See [`demo-spec.md`](./demo-spec.md) for the governing plan.

## Conventions

- These docs are **shared context**, not frozen. Keep them updated as the plan firms up.
- `project.md` is the live source of truth for the build; update it as decisions get made on the day.
