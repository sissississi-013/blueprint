# P&ID Copilot — Demo-Optimized Build Spec
### Dell × NVIDIA GB10 Hackathon · OpenClaw + NemoClaw + OpenShell

> **NEWEST / GOVERNING SPEC.** Combines the judging rubric, the research/report spec, and correct required-stack usage. Supersedes [`build-spec.md`](./build-spec.md) and [`project.md`](./project.md) on product shape: the build is now a **continuous, live red-lining copilot**, not a submit-a-file punch-list bot. `build-spec.md` remains the deep reference for datasets, rules, and model serving.

## The one-line pitch
**An always-on AI copilot that sits on top of the tools engineers already use, reads every P&ID revision they save, and red-lines safety and compliance violations in real time — running entirely on the Dell GB10, nothing leaving the box, nothing about their workflow changing.**

Grammarly's underlines, but for the engineering safety diagrams that refineries, chemical plants, and offshore platforms are built from. Catch the missing relief valve *as it's deleted*, not six weeks later in HAZOP or — worse — during construction.

---

## The reframe (why this version wins the rubric)
The original design was a "submit a file → get a punch-list" bot: reactive, one-shot, and it forces a submit on every edit. The judged product instead **runs a continuous validation loop over the live diagram state inside the OpenShell sandbox** and surfaces only what changed. Two consequences:
- **No dependency on the venue environment.** The watched diagram lives inside the sandbox on the GB10. We never need to mount a host drive or cloud folder.
- **Autonomy is provable on stage.** Make an edit; the agent reacts unprompted. That *is* "the agent acts on its own over time."

### Unifying design principle: everything is a graph
The human sees the agent's reasoning *on the drawing* (red nodes, ghost edges, matched subgraphs). The model reasons over the same graph structure — which is also the representation that scores ~18% higher than raw image/text input (ChatP&ID, arXiv 2603.22528). One representation, both sides. This is the wow factor and the technical-depth story at once.

### Governing constraint: the invisibility principle
**Nothing about the engineer's stack or behavior may change.** Engineers author in AutoCAD Plant 3D / SmartPlant / AVEVA / Bentley and exchange results as **PDFs, images, and sometimes DEXPI**. If the product demands they export a clean graph or draw in *our* canvas, we've forced a switch — the exact thing we must not do. We are an **overlay on the existing stack, not a replacement**: the agent reads whatever the existing stack already emits and a safety review just appears.

Separate three layers that are easy to collapse:

| Layer | What it is | Invisibility implication |
|---|---|---|
| **1 — Input boundary / workflow** | What the engineer touches (their authoring tool + the saves/exports they already produce) | **Must be invisible.** Accept their real artifacts: native smart-P&ID, DEXPI, **PDF, scanned image**. |
| **2 — Reasoning core** | What our engine reasons on | **Graph, always.** The whole ecosystem reasons on graphs; the user never sees this layer, so it costs zero behavior change. |
| **3 — Build order (one day)** | What we construct first | **Graph-first.** Graph datasets let us build the differentiated reasoning + red-lining; vision is a borrowable front-end we can't build well from scratch in a day. |

**The sharpening this forces:** invisibility is a Layer-1 argument, and it **promotes vision from "optional wow stretch" to the proof of the entire thesis.** To be invisible we must swallow the artifacts engineers already make — and a large share are images/PDFs. The pitch is literally *"keep drawing exactly how you draw, save your PDF like always, and a safety review appears."* You can't tell that story with a graph-only ingest. But invisibility is about the *input boundary*, not which component you build first — so the build order does **not** flip. You can be 100% invisible with a graph core as long as the input adapter swallows real artifacts.

**The `ingest()` contract — one interface, three adapters (the architecture lock):**

```
ingest(artifact) -> NetworkX graph        # one normalized graph, regardless of source
  ├── adapter: native DEXPI .xml  (pyDEXPI)        ← born-digital, zero vision  [BUILD NOW]
  ├── adapter: .graphml           (nx.read_graphml) ← benchmark/demo data       [BUILD NOW]
  ├── adapter: PDF                (extract → graph)  ← legacy/brownfield         [next]
  └── adapter: scanned image      (Nemotron Nano-12B-VL / detector → graph)     ← invisibility proof [thin, even if rough]
```

Everything downstream of `ingest()` is identical and graph-only. Adapters are added in invisibility-grain order: **start invisible for the born-digital segment** (read native smart-P&ID / DEXPI — graph, zero vision, zero behavior change), then **expand to legacy/PDF + scanned via the vision adapter.** Each step is invisible on its own terms; we never ask anyone to change how they work, we just read more of what they already make.

> **Net call:** graph for the core and the build, vision at the boundary. The invisibility principle is *precisely why vision can't be dropped entirely* — even though it isn't where we start. The product is an **ambient graph-reasoning copilot that sits on top of the existing stack and reads whatever it emits.**

---

## Rubric fit (explicit)
| Criterion | Wt | How this design scores |
|---|---|---|
| Local-first + always-on | 30% | Nemotron runs 100% on the GB10, zero cloud tokens; continuous validation loop reacts to every edit unprompted; OpenShell default-deny egress means the agent *cannot* phone home. |
| Business value | 30% | **Zero-switch adoption** — an overlay on AutoCAD/SmartPlant/AVEVA that reads what they already emit (DEXPI, PDF, scans), so there's no migration cost or behavior change. Catches API 521 / ISA-5.1 / IEC 61511 violations at the cheapest moment; rework is 5–12% of project cost; on-prem so plant IP never leaves the building (a purchasing requirement in oil & gas/pharma). |
| Demo + pitch | 30% | Live red-lining on the diagram as you "break" it — a legible, dramatic 5-min story (see Demo Script). |
| Technical execution | 10% | Real-time graph-diff + agent loop + live annotation + correct, load-bearing use of OpenClaw/NemoClaw/OpenShell. |

---

## Architecture

```
   engineer's real authoring tool (AutoCAD Plant 3D / SmartPlant / AVEVA ...)  ← UNCHANGED. They keep working here.
                          | saves / exports a revision (native smart-P&ID, DEXPI .xml, PDF, scanned image)
                          v
+----------------------------------------------- Dell Pro Max - GB10 -----------------------------------------------+
|                                                                                                                   |
|  [ Review pane ]  (ambient overlay, localhost web app: Cytoscape.js graph render of THEIR revision + findings)    |
|        |  ^   read-only to the engineer's workflow: an overlay, NOT an editor                                     |
|  new-revision | annotation commands (node->red, ghost-edge, callout)                                              |
|        v  |                                                                                                       |
|  +------------- OpenShell sandbox (Landlock/seccomp/netns, default-deny egress; allow localhost + Telegram) ----+ |
|  |  ingest(artifact) -> graph   [ DEXPI/.graphml now | PDF next | scanned-image (Nano-12B-VL) = invisibility ]   | |
|  |  [ OpenClaw agent ] -- tools --> ingest . validate_graph . annotate . explain_finding . diff_revisions       | |
|  |        |                                                                                                      | |
|  |        +- Rule engine (DETERMINISTIC): NetworkX + VF2 subgraph isomorphism + tag-grammar regex + reachability| |
|  |        |      -> punch-list JSON {rule_id, severity, node, message, standard_ref, ghost_edges}                | |
|  |        |                                                                                                      | |
|  |        +- Reviewer model (NemoClaw -> Nemotron, local): narrates WHY, answers graph Q&A, never invents       | |
|  +--------------------------------------------------------------------------------------------------------------+ |
|        |                                                                                                          |
|        v  NemoClaw Telegram/Slack bridge -> "Rev change: PSV-101 removed -> V-101 violates API 521"               |
+-------------------------------------------------------------------------------------------------------------------+
```

**Overlay, not replacement:** the engineer never opens our app to *work* — they keep authoring in their tool and saving revisions as they always have. Our review pane *watches* the revisions they emit (via the `ingest()` adapters) and red-lines each one. This is the honest embodiment of the invisibility principle.

**Division of labor that keeps it credible:** the **rule engine is deterministic** and produces the findings; **Nemotron only explains and answers questions.** The LLM never decides whether something is a violation — so it can't hallucinate a safety pass. This is your "doesn't break / technically sound" answer and it mirrors how the industry actually trusts these tools (human-in-the-loop).

---

## The continuous loop (the autonomy core)
1. The engineer **saves/exports a new revision in their own authoring tool** (or, in the demo, a scripted button stands in for that save). The agent picks it up and runs `ingest(artifact) -> G'` (graph from native/DEXPI/PDF/image).
2. Agent computes `diff(G, G')` -> only the affected components.
3. Rule engine re-validates the affected neighborhood (incremental, fast) and recomputes severity.
4. Agent emits annotation commands -> the review pane updates the red-lines live; NemoClaw posts a delta alert to Telegram.
5. State persists, so the agent can say *"PSV-101 was present last revision and is now gone"* — revision regression detection, the feature that proves "over time."

Incremental re-validation (not full re-scan) is both the autonomy story and a genuine bit of technical depth to mention in the pitch. Note the loop is driven by **their saves**, not by edits in our tool — autonomy *and* invisibility in one mechanism.

---

## WOW demo script (5 minutes)
1. **(0:15) The review pane.** A real OPEN100 P&ID renders in the side panel on the GB10's monitor. *"Engineers keep working in AutoCAD / SmartPlant exactly as they do today. Our agent just watches the revisions they save — running entirely on this Dell box, no cloud, fully sandboxed. Nothing about their workflow changes."*
2. **(0:45) Show it's clean + ask it something.** Green overlay: "47 checks passing." Type *"which vessels have relief protection?"* -> those vessels glow green on the graph. (Proves local Nemotron + graph Q&A.)
3. **(1:30) THE BREAK — a new revision lands.** Click **Delete PSV-101** — *framed as "an engineer just saved a new revision in AutoCAD"*, not an edit in our app. Instantly, no submit: V-101 pulses **red**, a **dashed ghost edge** appears showing the relief path that *should* exist, callout: *"V-101 unprotected — no relief path to flare (API 521)."* Telegram pings at the same moment. (Proves: always-on, continuous, visual reasoning, NemoClaw messaging, the safety catch.)
4. **(2:30) Next revision.** Duplicate a tag -> both nodes flash and link with a "duplicate" badge. Strip a control valve's fail position -> it turns amber. The agent keeps up with each saved revision, no prompting. (Proves continuous autonomy, not one-shot.)
5. **(3:30) Click a finding -> "why?"** Nemotron explains in plain language, cites the standard, and the pane **highlights the subgraph pattern it matched** (visual reasoning trace). (Proves depth + explainability.)
6. **(4:00) Invisibility proof — feed it a real PDF/image.** Drop an actual P&ID PDF (or screenshot) the way an engineer would have it -> `ingest()` runs the vision adapter (Nano-12B-VL) -> same graph -> same review appears. *"We read what you already have. No export, no new format, no behavior change."* (Even if rough, this is the move that makes judges feel the zero-switch thesis.)
7. **(4:30) Close on business.** *"Every revision validated the instant it's saved — before HAZOP, before construction, when fixes are cheapest. We sit on top of your existing tools and read whatever they emit. Fully on-prem, so the plant's IP never leaves the building. Sandboxed, so the agent can't exfiltrate it. That's continuous, invisible compliance."*

**Wow levers to rehearse:** the *instant* red-line on a saved revision (no submit, no tool switch); the **ghost edge** drawing the missing thing (showing what *should* be there is more striking than just flagging what's wrong); the simultaneous Telegram ping; the live subgraph-match highlight; and the **PDF/image ingest** that proves "we read what you already make."

---

## Validation checks (prioritized for the demo)
Deterministic, on the graph. Build top-down; each is a clean visual.
1. **Vessel has no relief path** (API 521) — reachability vessel->PSV/PSE->disposal sink. *Ghost edge = the missing path.* <- lead with this.
2. **Duplicate instrument tag** — classic real error; visually links the offenders.
3. **Control valve missing fail position** (FO/FC/FL) — attribute check; amber node.
4. **Vessel missing level instrument** (Schulze Balhorn Rule 9, mandatory) — VF2 pattern.
5. **Pump protection set** — discharge check valve (Rule 19), suction strainer (Rule 10), block valves + drain (Rule 21).
6. **ISA-5.1 tag grammar** — first-letter in valid variable set, valid succeeding letters, loop number present.

Stretch: PSV isolatable by a closed block valve; SIS/BPCS separation (IEC 61511); dangling/orphan nodes.

Rule source for the VF2 patterns: Schulze Balhorn et al., *Rule-Based Autocorrection of P&IDs on Graphs*, arXiv 2502.18493 (33 rules, runs in ms via NetworkX VF2).

---

## Build plan (single day, ~10 hr)
**Pre-day on the MacBook -> 64 GB USB:** `nemotron-3-nano` (Nano-30B UD-Q4 GGUF, ~24 GB) + datasets (PID2Graph `.zip`, pyDEXPI repo) + clone NemoClaw + npm-vendor Cytoscape.js. Skip Super-120B (won't co-fit; Nano-30B is the workhorse and is fast enough interactively).

- **H0-1 . Stack up.** Copy from USB; `ollama serve`; load Nano-30B; `nemoclaw onboard`; OpenShell policy = allow localhost + Telegram; round-trip a "hello" Telegram->Nemotron->Telegram.
- **H1-2.5 . `ingest()` + review pane.** Define `ingest(artifact) -> NetworkX graph` with the **DEXPI** (`pyDEXPI`) and **`.graphml`** (`nx.read_graphml`) adapters; normalize attrs (tag, type, fail_position, line_no). Stand up the Cytoscape.js **review pane** rendering the graph; add 3 scripted **"new revision saved"** buttons (Delete PSV-101, Duplicate tag, Strip fail position) — framed as the engineer's saves, not edits in our app.
- **H2.5-5 . Rule engine.** Checks 1-6 as Python functions + 2 VF2 patterns. Emit punch-list JSON incl. `ghost_edges`. Wire `new-revision` -> `diff` -> validate -> annotation commands -> pane re-render.
- **H5-6 . Agent wiring.** OpenClaw tools (`ingest`, `validate_graph`, `annotate`, `explain_finding`, `diff_revisions`); Nemotron narrates + answers Q&A; never authors findings.
- **H6-7 . Always-on + alerts.** Continuous loop + revision-diff state; NemoClaw Telegram delta alerts.
- **H7-8.5 . Polish the wow.** Ghost-edge animation, red/amber/green styling, subgraph-match highlight, the green "N passing" overlay.
- **H8.5-9.5 . Vision adapter (invisibility proof).** Add a **thin** `ingest()` PDF/image adapter via Nemotron Nano-12B-VL (or a pretrained detector) -> graph. Accuracy is *not* the goal; demonstrating "we read what you already have" is. One real PDF/screenshot must round-trip to a review.
- **H9.5-10 . Rehearse + fallbacks.** Run the 5-min script ~3x; freeze a known-good graph + scripted revisions; pre-test the one PDF used in step 6.

---

## Required-stack correctness (say this to judges)
- **OpenClaw** — the agent itself; orchestrates tools and the validation loop.
- **NemoClaw** — serves the local Nemotron model and provides the Telegram/Slack bridge for always-on alerts.
- **OpenShell** — sandboxes the whole agent (Landlock/seccomp/netns), default-deny egress; the canvas reaches it only over an allowed localhost endpoint. This *is* the "agent can't exfiltrate your plant IP" security pitch.

All three are load-bearing, not decorative. Do **not** demo via a bare `python-telegram-bot` bypass — the rubric scores correct stack use; keep that only as a private emergency parachute.

---

## Risk / fallback
- **Review pane is the new risk.** Mitigate: it only needs to *render* the graph + apply annotation classes + run 3 *scripted* "new revision" buttons — not a full editor (which would also violate invisibility). Scripted revisions are better for a demo anyway (deterministic, you control the beat).
- **If the pane slips**, fall back to Telegram-only: post the annotated graph as a rendered PNG (NetworkX/Graphviz) per revision. Less wow, same rubric coverage, still invisible.
- **Vision adapter is rough / inaccurate** -> that's acceptable. It's the *invisibility proof*, not the core; keep one hand-checked PDF that round-trips cleanly for the demo, and lean on the DEXPI/`.graphml` adapters for everything else. Do **not** let vision block the graph core.
- **Nemotron too slow for live narration** -> narration is async and non-blocking; the red-line (rule engine) is instant regardless. Use Nano-30B, not Super-120B, for anything interactive.
- **NemoClaw early-preview breaks** -> it's load-bearing for scoring, so debug it first (H0-1) rather than route around it; keep the bare bridge only as last resort.
- **False positives** -> rules are deterministic + conservative; everything framed as a human-in-the-loop punch-list, never auto-approval.

---

## Resource pointers (detail lives in the research doc)
- **`ingest()` graph adapters (build now, skip detection):** PID2Graph `.graphml` -> `wget` from Zenodo 14803338 -> `nx.read_graphml`. pyDEXPI parses DEXPI `.xml` and can generate synthetic P&IDs (fabricate your known-bad demo case: inject the missing PSV + duplicate tag).
- **`ingest()` vision adapter (invisibility proof, thin):** Nemotron **Nano-12B-v2-VL** (`nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-*`, OCRBench-v2 leader) or a pretrained detector (e.g. ASU `mgupta70/PID_Symbol_Detection`) -> graph. PDF text/structure extraction first; image only when there's no embedded text.
- **Rules:** arXiv 2502.18493 (VF2 rule-graphs); ISA-5.1 letter tables (EngineeringToolBox / InstruNexus); API 521 + IEC 61511 summaries (iFluids checklist).
- **Model:** Nano-30B via Ollama (`ollama run nemotron-3-nano`) for reasoning/narration; Nano-12B-v2-VL for the vision adapter.
- **Review pane:** Cytoscape.js (graph-native styling, dynamic class changes for red-lining) — an overlay, not an editor.
- **Stack:** github.com/NVIDIA/NemoClaw · docs.nvidia.com/nemoclaw.

> Full datasets, exact download commands, the complete rule set, and Nemotron model IDs/serving commands live in [`build-spec.md`](./build-spec.md).
