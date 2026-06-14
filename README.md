# blueprint

**An always-on, fully local copilot that live red-lines Piping & Instrumentation Diagrams (P&IDs) as engineers edit them.**

`blueprint` is the **P&ID Copilot**: it watches a live engineering diagram and, the instant an edit introduces a safety or compliance violation, red-lines it directly on the drawing — pulsing the offending node red, drawing a *ghost edge* for the relief path that should exist, and pinging Telegram — all without a submit. "Grammarly's underlines, but for the engineering safety diagrams that refineries, chemical plants, and offshore platforms are built from." Catch the missing relief valve *as it's deleted*, not six weeks later in HAZOP. Everything runs on-device on the **Dell Pro Max with GB10**; no engineering drawings ever leave the box.

> Built for the **Dell × NVIDIA Hackathon — "Local AI on Dell Pro Max with GB10"** (San Francisco, June 14, 2026).

**Required stack:** OpenClaw + NVIDIA NemoClaw + OpenShell, powered by NVIDIA Nemotron 3 — all running locally on the GB10.

**Judged on:** Local-first + always-on (30%) · Business value (30%) · Demo + pitch (30%) · Technical execution (10%). The agent runs a **continuous validation loop** over live diagram state and reacts to every edit unprompted — autonomy that's provable on stage, not a request-response chatbot.

---

## Why

P&ID pain is **review and compliance**, not drafting. Digitization and Q&A are largely solved in the 2024–2026 literature, but **automated rule-based compliance validation** (ISA-5.1 checks, missing relief valves/interlocks) exists only as "future work." The one published quantitative attempt at LLM HAZOP reasoning found semantically-valid scenarios at just **0.19–0.37**. That gap — on confidential, on-prem engineering data — is the wedge.

ROI framing: *"Finding a numbering error at issued-for-construction costs hours; finding it during construction costs days and material write-offs."*

## Architecture

**Everything is a graph.** A live diagram canvas emits change events; a **deterministic** rule engine finds violations; a local LLM only *explains* them. We deliberately do **not** ask a vision model to "read the whole diagram" — the LLM never decides whether something is a violation, so it can't hallucinate a safety pass.

```
[ Cytoscape.js canvas on the GB10 ]  ──graph-changed──▶  [ diff(G, G') ]  ──▶  [ rule engine ]  ──annotations──▶  back to canvas (red node / ghost edge / callout)
   (renders graph, scripted edits)                          (affected nbhd)    (NetworkX + VF2 + tag-grammar      └─▶ Nemotron narrates "why" + Q&A (never authors findings)
                                                                                + reachability → punch-list JSON)  └─▶ NemoClaw → Telegram delta alert
```

- **Deterministic core:** rule engine (NetworkX + VF2 subgraph isomorphism + ISA-5.1 tag grammar + relief-path reachability) produces every finding; Nemotron only narrates.
- **Always-on loop:** incremental re-validation of the changed neighborhood on each edit; revision-diff state detects regressions ("PSV-101 was present last revision and is now gone").
- **Orchestration:** OpenClaw (agent + tools + loop) on the NVIDIA NemoClaw reference stack.
- **Sandbox:** OpenShell (Landlock/seccomp/netns, default-deny egress) — the agent *cannot* exfiltrate plant IP.
- **Models:** NVIDIA Nemotron 3 Nano-30B (interactive workhorse, local via Ollama); Nano-12B VL only for the optional "drop a screenshot" stretch.
- **Runtime:** 100% local on the GB10 — zero cloud tokens.

## Repository layout

```
blueprint/
├── docs/                 # Shared context window for the build (read this first)
│   ├── README.md                       # Index of the docs
│   ├── demo-spec.md                    # ⭐ Governing spec: the P&ID Copilot (product shape)
│   ├── build-spec.md                   # Deep impl reference: datasets, rule set, model serving
│   ├── project.md                      # Earliest framing (superseded; kept for context)
│   ├── hackathon-context.md            # Event rules, rubric, prizes, logistics
│   └── sponsor-tech-and-advantages.md  # Hardware/models/stack deep dive + leverage
├── src/                  # App code (canvas + agent + rule engine)  [planned]
├── README.md
└── LICENSE               # MIT
```

## Status

> Keep this section current — it is the at-a-glance build state.

**Phase: pre-build / planning.** Spec and context locked in `docs/`. Code scaffolding not yet started.

| Component | State |
|---|---|
| Docs / spec (`docs/`) | ✅ Done |
| NemoClaw + Nemotron (Nano-30B) on GB10 | ⬜ Not started |
| Graph load (PID2Graph `.graphml` / pyDEXPI) + normalize | ⬜ Not started |
| Cytoscape.js canvas + scripted edit buttons | ⬜ Not started |
| Deterministic rule engine (checks 1–6, VF2 patterns) + ghost-edges | ⬜ Not started |
| Continuous loop (graph-diff, incremental re-validate, revision state) | ⬜ Not started |
| OpenClaw tools + Nemotron narration / Q&A | ⬜ Not started |
| NemoClaw Telegram delta alerts | ⬜ Not started |

See [`docs/demo-spec.md`](docs/demo-spec.md) for the governing plan, 5-min demo script, and hour-by-hour build plan.

## Getting started

The build runs on the GB10 on-site. See [`docs/demo-spec.md`](docs/demo-spec.md) (Build plan) for staging and [`docs/build-spec.md`](docs/build-spec.md) for the NemoClaw install path, dataset downloads, and Nemotron serving commands. Code on a laptop is fine, but the final demo must run on the box.

## License

[MIT](LICENSE)
