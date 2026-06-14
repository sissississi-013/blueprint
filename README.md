# blueprint

**An always-on, fully local agent that validates Piping & Instrumentation Diagrams (P&IDs).**

`blueprint` ingests a P&ID, extracts a connectivity graph, and runs a local NVIDIA Nemotron model as an automated reviewer that returns a **compliance punch-list** — ISA-5.1 tag validity, line-number / tag cross-validation, and missing safety instrumentation — each finding tied to the standard it violates. Everything runs on-device on the **Dell Pro Max with GB10**; no engineering drawings ever leave the box.

> Built for the **Dell × NVIDIA Hackathon — "Local AI on Dell Pro Max with GB10"** (San Francisco, June 14, 2026).

**Required stack:** OpenClaw + NVIDIA NemoClaw + OpenShell, powered by NVIDIA Nemotron 3 — all running locally on the GB10.

**Judged on:** Local-first + always-on (30%) · Business value (30%) · Demo + pitch (30%) · Technical execution (10%). The agent is designed to be **proactive** — it watches for new drawings and emits a punch-list on its own, not a request-response chatbot.

---

## Why

P&ID pain is **review and compliance**, not drafting. Digitization and Q&A are largely solved in the 2024–2026 literature, but **automated rule-based compliance validation** (ISA-5.1 checks, missing relief valves/interlocks) exists only as "future work." The one published quantitative attempt at LLM HAZOP reasoning found semantically-valid scenarios at just **0.19–0.37**. That gap — on confidential, on-prem engineering data — is the wedge.

ROI framing: *"Finding a numbering error at issued-for-construction costs hours; finding it during construction costs days and material write-offs."*

## Architecture

Trained detector → **deterministic** graph → LLM reasoner. We deliberately do **not** ask a vision model to "read the whole diagram" (VLMs are weak at raw diagram reasoning); the LLM reasons over a structured graph instead.

```
P&ID image ──▶ symbol/text/line detector ──▶ NetworkX connectivity graph ──▶ Nemotron reviewer ──▶ punch-list
   (open datasets / scan)   (YOLOv5 / Detectron2)    (nodes=tags, edges=lines)   (ISA-5.1 + safety rules)   (Telegram/Slack)
```

- **Orchestration:** OpenClaw (always-on gateway) + NVIDIA NemoClaw reference stack
- **Sandbox:** OpenShell (deny-by-default network + filesystem isolation, live policy approval)
- **Models:** NVIDIA Nemotron 3 — Nano (fast lane / interactive), Super 120B (deep reasoning), Nano Omni / V2 VL (multimodal legend reading)
- **Runtime:** 100% local on the GB10 via Ollama / vLLM

## Repository layout

```
blueprint/
├── docs/                 # Shared context window for the build (read this first)
│   ├── README.md                       # Index of the docs
│   ├── project.md                      # The build spec + hour-by-hour playbook (source of truth)
│   ├── hackathon-context.md            # Event rules, stack, prizes, logistics
│   └── sponsor-tech-and-advantages.md  # Hardware/models/stack deep dive + leverage
├── src/                  # Pipeline code (detector → graph → reviewer)  [planned]
├── README.md
└── LICENSE               # MIT
```

## Status

> Keep this section current — it is the at-a-glance build state.

**Phase: pre-build / planning.** Spec and context locked in `docs/`. Code scaffolding not yet started.

| Component | State |
|---|---|
| Docs / spec (`docs/`) | ✅ Done |
| NemoClaw + Nemotron on GB10 | ⬜ Not started |
| Detector / dataset ingest (PID2Graph `.graphml` fast-path) | ⬜ Not started |
| NetworkX graph builder + renderer | ⬜ Not started |
| Reviewer agent (ISA-5.1 + cross-validation + safety checks) | ⬜ Not started |
| Punch-list output (Telegram/Slack) + GraphRAG Q&A | ⬜ Not started |

See [`docs/project.md`](docs/project.md) for the staged hour-0→8 build plan and decision thresholds.

## Getting started

The build runs on the GB10 on-site. See [`docs/project.md`](docs/project.md) (Build Playbook) for the NemoClaw install path and staging. Code on a laptop is fine, but the final demo must run on the box.

## License

[MIT](LICENSE)
