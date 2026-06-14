# blueprint

**An always-on, fully local copilot that sits on top of engineers' existing tools and live red-lines Piping & Instrumentation Diagrams (P&IDs) as new revisions are saved.**

`blueprint` is the **P&ID Copilot**: an *overlay* on the tools engineers already use (AutoCAD Plant 3D / SmartPlant / AVEVA). It reads every revision they save and, the instant one introduces a safety or compliance violation, red-lines it on a review pane — pulsing the offending node red, drawing a *ghost edge* for the relief path that should exist, and pinging Telegram — all without a submit and **without changing anything about their workflow**. "Grammarly's underlines, but for the engineering safety diagrams that refineries, chemical plants, and offshore platforms are built from." An `ingest()` contract swallows their real artifacts (native DEXPI / `.graphml` today; PDF and scanned image via a Nemotron vision adapter). Everything runs on-device on the **Dell Pro Max with GB10**; no engineering drawings ever leave the box.

> Built for the **Dell × NVIDIA Hackathon — "Local AI on Dell Pro Max with GB10"** (San Francisco, June 14, 2026).

**Required stack:** OpenClaw + NVIDIA NemoClaw + OpenShell, powered by NVIDIA Nemotron 3 — all running locally on the GB10.

**Judged on:** Local-first + always-on (30%) · Business value (30%) · Demo + pitch (30%) · Technical execution (10%). The agent runs a **continuous validation loop** over live diagram state and reacts to every edit unprompted — autonomy that's provable on stage, not a request-response chatbot.

---

## Why

P&ID pain is **review and compliance**, not drafting. Digitization and Q&A are largely solved in the 2024–2026 literature, but **automated rule-based compliance validation** (ISA-5.1 checks, missing relief valves/interlocks) exists only as "future work." The one published quantitative attempt at LLM HAZOP reasoning found semantically-valid scenarios at just **0.19–0.37**. That gap — on confidential, on-prem engineering data — is the wedge.

ROI framing: *"Finding a numbering error at issued-for-construction costs hours; finding it during construction costs days and material write-offs."*

## Architecture

**Everything is a graph; invisibility governs the boundary.** Engineers keep working in their own tools and saving revisions as they always have. An `ingest()` adapter turns each saved artifact into a graph; a **deterministic** rule engine finds violations; a local LLM only *explains* them. The LLM never decides whether something is a violation, so it can't hallucinate a safety pass.

```
their tool (AutoCAD/SmartPlant/AVEVA) ──saves revision──▶ ingest(artifact) ──▶ [ diff(G, G') ] ──▶ [ rule engine ] ──annotations──▶ review pane (red node / ghost edge / callout)
   (UNCHANGED workflow)        (DEXPI/.graphml now;          (NetworkX graph)    (affected nbhd)    (VF2 + tag-grammar      ├─▶ Nemotron narrates "why" + Q&A (never authors findings)
                               PDF/image via Nano-12B-VL)                                            + reachability)        └─▶ NemoClaw → Telegram delta alert
```

- **Invisibility principle:** an overlay, not a replacement. `ingest()` = one interface, three adapters (native DEXPI / `.graphml` now → PDF → scanned-image vision adapter). Vision at the boundary is the *proof* of "nothing changed," not an afterthought.
- **Deterministic core:** rule engine (NetworkX + VF2 subgraph isomorphism + ISA-5.1 tag grammar + relief-path reachability) produces every finding; Nemotron only narrates.
- **Always-on loop:** incremental re-validation of the changed neighborhood on each saved revision; revision-diff state detects regressions ("PSV-101 was present last revision and is now gone").
- **Orchestration:** OpenClaw (agent + tools + loop) on the NVIDIA NemoClaw reference stack.
- **Sandbox:** OpenShell (Landlock/seccomp/netns, default-deny egress) — the agent *cannot* exfiltrate plant IP.
- **Models:** NVIDIA Nemotron 3 Nano-30B (interactive reasoning/narration, local via Ollama); Nano-12B VL for the vision ingest adapter.
- **Runtime:** 100% local on the GB10 — zero cloud tokens.

## Repository layout

```
blueprint/
├── docs/                 # Shared context window for the build (read this first)
│   ├── README.md                       # Index of the docs
│   ├── build-plan.md                   # 🛠️ The actionable engineering build plan (start coding here)
│   ├── demo-spec.md                    # ⭐ Governing spec: the P&ID Copilot (product shape)
│   ├── build-spec.md                   # Deep impl reference: datasets, rule set, model serving
│   ├── project.md                      # Earliest framing (superseded; kept for context)
│   ├── hackathon-context.md            # Event rules, rubric, prizes, logistics
│   └── sponsor-tech-and-advantages.md  # Hardware/models/stack deep dive + leverage
├── pidcopilot/           # Python brain: graph schema, ingest adapters, rule engine, server
│   ├── graph/            # canonical schema + revision diff
│   ├── ingest/           # dexpi / graphml / drawio / vision adapters + dispatcher
│   ├── rules/            # engine + R1–R4 (+ R5/R6 stretch) with ProposedFix + apply_fix
│   ├── demo/             # synthetic backbone + scripted revisions
│   ├── llm/ · alerts/ · agent/   # Nemotron client, Telegram, prompt contracts
│   └── server.py         # FastAPI + WebSocket + Python-owned watcher heartbeat
├── web/                  # Cytoscape.js review pane (index.html / pane.js / style.css)
├── scripts/verify_demo_graph.py   # PRE-DAY check: do R1–R4 have something to fire on?
├── tests/                # rule unit tests (8 passing)
├── requirements.txt · run.sh
├── README.md
└── LICENSE               # MIT
```

## Run it (laptop)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scripts/verify_demo_graph.py        # confirms the demo graph satisfies R1–R4
pytest -q                                  # 8 rule tests
./run.sh                                   # serve the brain + pane at http://127.0.0.1:8000
```

The deterministic core (ingest → rules → suggest-the-fix → pane) runs fully offline with no model. Nemotron (via NemoClaw) only narrates; Telegram is optional. On the GB10 the agent face + inference are added on top.

## Status

> Keep this section current — it is the at-a-glance build state.

**Phase: core scaffold built & tested on laptop; stack integration pending on the GB10.**

| Component | State |
|---|---|
| Docs / spec (`docs/`) | ✅ Done |
| Canonical graph schema + revision diff | ✅ Built |
| Deterministic rule engine R1–R4 + `ProposedFix` + `apply_fix` (suggest-the-fix) | ✅ Built + tested |
| Synthetic demo backbone + scripted revisions + pre-day verify script | ✅ Built (verify passes) |
| `ingest()` adapters: DEXPI / `.graphml` / draw.io | ✅ Built (DEXPI API to confirm on-site) |
| Review pane (Cytoscape.js) + scripted "new revision" buttons + Accept-fix | ✅ Built |
| FastAPI server + WebSocket + Python-owned watcher heartbeat | ✅ Built + smoke-tested |
| Nemotron narration / Q&A client + Telegram alert formatter | ✅ Built (stubs; wire to model on box) |
| `ingest()` vision adapter (PDF / image → graph) — invisibility proof | 🟡 Stub (stretch) |
| NemoClaw + Nemotron (Nano-30B) served on GB10 | ⬜ On-site |
| OpenClaw agent face (skills/tools) + NemoClaw Telegram bridge | ⬜ On-site |
| draw.io offline on ARM + custom stencil round-trip | ⬜ On-site (verify) |

See [`docs/build-plan.md`](docs/build-plan.md) for the actionable engineering plan (data contracts, rule logic, configs, hour-by-hour) and [`docs/demo-spec.md`](docs/demo-spec.md) for product shape + the 5-min demo script.

## Getting started

The build runs on the GB10 on-site. **[`docs/build-plan.md`](docs/build-plan.md) is the entry point for coding** — file structure, data contracts, the rule engine, and the pre-day USB checklist. See [`docs/build-spec.md`](docs/build-spec.md) for the NemoClaw install path, dataset downloads, and Nemotron serving commands. Code on a laptop is fine, but the final demo must run on the box.

## License

[MIT](LICENSE)
