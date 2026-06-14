# Docs — Hackathon Context Window

This folder is the shared **context window** for the Dell × NVIDIA Hackathon ("Local AI on Dell Pro Max with GB10," June 14, 2026, San Francisco). Any agent working in this repository should read these files first to understand the event, the required stack, and the strategy.

## Files

| File | What's in it |
|---|---|
| [`project.md`](./project.md) | **What we're building today: the "P&ID Reviewer" — a local engineering-diagram validation agent.** Full spec, architecture (detector → graph → LLM reasoner), model choices, staged build playbook, resources to clone, and risks. **Read this first** to know the plan. |
| [`hackathon-context.md`](./hackathon-context.md) | The event itself: overview, challenge, required stack, teams, prizes, rules, FAQ, logistics, and application status. Read for "what are the rules / constraints." |
| [`sponsor-tech-and-advantages.md`](./sponsor-tech-and-advantages.md) | Deep dive on the hardware (GB10), the models (Nemotron 3), and the stack (OpenClaw + NemoClaw + OpenShell), plus the "unfair advantages" to exploit. Read for "why this stack, what to leverage." |

## The One-Paragraph Summary

Build a **business/corporate AI agent that runs 100% locally** on the Dell Pro Max with GB10, using the required stack: **OpenClaw** (always-on agent framework) + **NVIDIA NemoClaw** (reference distribution) + **OpenShell** (governance-first sandbox), powered by **NVIDIA Nemotron 3** models. The winning thesis is **local + private + always-on**: zero data egress, visible governance, frontier-class models on-device with 128 GB unified memory and up to 1M-token context. Ship a working demo that runs on the box, in one day.

## What We're Building

The **P&ID Reviewer**: an always-on local agent that ingests a piping & instrumentation diagram and returns a **compliance punch-list** — ISA-5.1 tag validity, line-number/tag cross-validation, and missing safety instrumentation — each finding tied to the standard it violates. Pipeline: trained **detector → deterministic NetworkX graph → local Nemotron reasoner**, sandboxed by OpenShell, output over Telegram/Slack. The wedge is a real, unfilled gap: P&ID *digitization and Q&A* are solved in the literature, but *automated compliance validation* is not. See [`project.md`](./project.md) for the full plan.

## Conventions

- These docs are **shared context**, not frozen. Keep them updated as the plan firms up.
- `project.md` is the live source of truth for the build; update it as decisions get made on the day.
