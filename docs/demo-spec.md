# P&ID Copilot — Demo-Optimized Build Spec
### Dell × NVIDIA GB10 Hackathon · OpenClaw + NemoClaw + OpenShell

> **NEWEST / GOVERNING SPEC.** Combines the judging rubric, the research/report spec, and correct required-stack usage. Supersedes [`build-spec.md`](./build-spec.md) and [`project.md`](./project.md) on product shape: the build is now a **continuous, live red-lining copilot**, not a submit-a-file punch-list bot. `build-spec.md` remains the deep reference for datasets, rules, and model serving.

## The one-line pitch
**An always-on AI copilot that watches engineers edit a P&ID and red-lines safety and compliance violations on the drawing in real time — running entirely on the Dell GB10, nothing leaving the box.**

Grammarly's underlines, but for the engineering safety diagrams that refineries, chemical plants, and offshore platforms are built from. Catch the missing relief valve *as it's deleted*, not six weeks later in HAZOP or — worse — during construction.

---

## The reframe (why this version wins the rubric)
The original design was a "submit a file → get a punch-list" bot: reactive, one-shot, and it forces a submit on every edit. The judged product instead **runs a continuous validation loop over the live diagram state inside the OpenShell sandbox** and surfaces only what changed. Two consequences:
- **No dependency on the venue environment.** The watched diagram lives inside the sandbox on the GB10. We never need to mount a host drive or cloud folder.
- **Autonomy is provable on stage.** Make an edit; the agent reacts unprompted. That *is* "the agent acts on its own over time."

### Unifying design principle: everything is a graph
The human sees the agent's reasoning *on the drawing* (red nodes, ghost edges, matched subgraphs). The model reasons over the same graph structure — which is also the representation that scores ~18% higher than raw image/text input (ChatP&ID, arXiv 2603.22528). One representation, both sides. This is the wow factor and the technical-depth story at once.

---

## Rubric fit (explicit)
| Criterion | Wt | How this design scores |
|---|---|---|
| Local-first + always-on | 30% | Nemotron runs 100% on the GB10, zero cloud tokens; continuous validation loop reacts to every edit unprompted; OpenShell default-deny egress means the agent *cannot* phone home. |
| Business value | 30% | Catches API 521 / ISA-5.1 / IEC 61511 violations at the cheapest moment; rework is 5–12% of project cost; on-prem so plant IP never leaves the building (a purchasing requirement in oil & gas/pharma). |
| Demo + pitch | 30% | Live red-lining on the diagram as you "break" it — a legible, dramatic 5-min story (see Demo Script). |
| Technical execution | 10% | Real-time graph-diff + agent loop + live annotation + correct, load-bearing use of OpenClaw/NemoClaw/OpenShell. |

---

## Architecture

```
+----------------------------------------------- Dell Pro Max - GB10 -----------------------------------------------+
|                                                                                                                   |
|  [ Canvas UI ]  (localhost web app on the box: Cytoscape.js graph render + scripted "edit" buttons)               |
|        |  ^                                                                                                       |
|  graph-changed | annotation commands (node->red, ghost-edge, callout)                                             |
|        v  |                                                                                                       |
|  +------------- OpenShell sandbox (Landlock/seccomp/netns, default-deny egress; allow localhost + Telegram) ----+ |
|  |  [ OpenClaw agent ] -- tools --> load_graph . validate_graph . annotate . explain_finding . diff_revisions   | |
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

**Division of labor that keeps it credible:** the **rule engine is deterministic** and produces the findings; **Nemotron only explains and answers questions.** The LLM never decides whether something is a violation — so it can't hallucinate a safety pass. This is your "doesn't break / technically sound" answer and it mirrors how the industry actually trusts these tools (human-in-the-loop).

---

## The continuous loop (the autonomy core)
1. Canvas holds the current graph `G`. On any edit (node/edge add/delete/attr-change), it emits a `graph-changed` event with the new `G'`.
2. Agent computes `diff(G, G')` -> only the affected components.
3. Rule engine re-validates the affected neighborhood (incremental, fast) and recomputes severity.
4. Agent emits annotation commands -> canvas updates the red-lines live; NemoClaw posts a delta alert to Telegram.
5. State persists, so the agent can say *"PSV-101 was present last revision and is now gone"* — revision regression detection, the feature that proves "over time."

Incremental re-validation (not full re-scan) is both the autonomy story and a genuine bit of technical depth to mention in the pitch.

---

## WOW demo script (5 minutes)
1. **(0:15) Open the canvas.** A real OPEN100 P&ID renders as a clean interactive graph on the GB10's monitor. *"This is a live engineering diagram. Our agent is watching it continuously — running entirely on this Dell box, no cloud, fully sandboxed."*
2. **(0:45) Show it's clean + ask it something.** Green overlay: "47 checks passing." Type *"which vessels have relief protection?"* -> those vessels glow green on the graph. (Proves local Nemotron + graph Q&A.)
3. **(1:30) THE BREAK.** Click **Delete PSV-101** (an engineer "editing"). Instantly, no submit: V-101 pulses **red**, a **dashed ghost edge** appears showing the relief path that *should* exist, callout: *"V-101 unprotected — no relief path to flare (API 521)."* Telegram pings at the same moment. (Proves: always-on, continuous, visual reasoning, NemoClaw messaging, the safety catch.)
4. **(2:30) Keep editing.** Duplicate a tag -> both nodes flash and link with a "duplicate" badge. Remove a control valve's fail position -> it turns amber. The agent keeps up live, no prompting. (Proves continuous autonomy, not one-shot.)
5. **(3:30) Click a finding -> "why?"** Nemotron explains in plain language, cites the standard, and the canvas **highlights the subgraph pattern it matched** (visual reasoning trace). (Proves depth + explainability.)
6. **(4:30) Close on business.** *"Every revision validated the instant it's made — before HAZOP, before construction, when fixes are cheapest. Fully on-prem, so the plant's IP never leaves the building. Sandboxed, so the agent can't exfiltrate it. That's continuous compliance."*

**Wow levers to rehearse:** the *instant* red-line with no submit; the **ghost edge** drawing the missing thing (showing what *should* be there is more striking than just flagging what's wrong); the simultaneous Telegram ping; the live subgraph-match highlight.

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
- **H1-2.5 . Graph + canvas.** `nx.read_graphml` / pyDEXPI -> normalized graph (tag, type, fail_position, line_no). Stand up the Cytoscape.js canvas rendering the graph; add 3 scripted edit buttons (Delete PSV-101, Duplicate tag, Strip fail position).
- **H2.5-5 . Rule engine.** Checks 1-6 as Python functions + 2 VF2 patterns. Emit punch-list JSON incl. `ghost_edges`. Wire `graph-changed` -> validate -> annotation commands -> canvas re-render.
- **H5-6 . Agent wiring.** OpenClaw tools (`load_graph`, `validate_graph`, `annotate`, `explain_finding`, `diff_revisions`); Nemotron narrates + answers Q&A; never authors findings.
- **H6-7 . Always-on + alerts.** Continuous loop + revision-diff state; NemoClaw Telegram delta alerts.
- **H7-8.5 . Polish the wow.** Ghost-edge animation, red/amber/green styling, subgraph-match highlight, the green "N passing" overlay.
- **H8.5-10 . Rehearse + fallbacks.** Run the 5-min script ~3x; freeze a known-good graph + scripted edits.

---

## Required-stack correctness (say this to judges)
- **OpenClaw** — the agent itself; orchestrates tools and the validation loop.
- **NemoClaw** — serves the local Nemotron model and provides the Telegram/Slack bridge for always-on alerts.
- **OpenShell** — sandboxes the whole agent (Landlock/seccomp/netns), default-deny egress; the canvas reaches it only over an allowed localhost endpoint. This *is* the "agent can't exfiltrate your plant IP" security pitch.

All three are load-bearing, not decorative. Do **not** demo via a bare `python-telegram-bot` bypass — the rubric scores correct stack use; keep that only as a private emergency parachute.

---

## Risk / fallback
- **Canvas is the new risk.** Mitigate: it only needs to *render* + run 3 *scripted* mutation buttons — not a full editor. Scripted edits are also better for a demo (deterministic, you control the beat).
- **If the canvas slips**, fall back to Telegram-only: post the annotated graph as a rendered PNG (NetworkX/Graphviz) per edit. Less wow, same rubric coverage.
- **Nemotron too slow for live narration** -> narration is async and non-blocking; the red-line (rule engine) is instant regardless. Use Nano-30B, not Super-120B, for anything interactive.
- **NemoClaw early-preview breaks** -> it's load-bearing for scoring, so debug it first (H0-1) rather than route around it; keep the bare bridge only as last resort.
- **False positives** -> rules are deterministic + conservative; everything framed as a human-in-the-loop punch-list, never auto-approval.

---

## Resource pointers (detail lives in the research doc)
- **Graphs (skip detection):** PID2Graph `.graphml` -> `wget` from Zenodo 14803338 -> `nx.read_graphml`. pyDEXPI parses DEXPI `.xml` and can generate synthetic P&IDs (fabricate your known-bad demo case: inject the missing PSV + duplicate tag).
- **Rules:** arXiv 2502.18493 (VF2 rule-graphs); ISA-5.1 letter tables (EngineeringToolBox / InstruNexus); API 521 + IEC 61511 summaries (iFluids checklist).
- **Model:** Nano-30B via Ollama (`ollama run nemotron-3-nano`); Nano-12B-v2-VL only if you add the "drop a screenshot" stretch.
- **Canvas:** Cytoscape.js (graph-native styling, dynamic class changes for red-lining).
- **Stack:** github.com/NVIDIA/NemoClaw · docs.nvidia.com/nemoclaw.

> Full datasets, exact download commands, the complete rule set, and Nemotron model IDs/serving commands live in [`build-spec.md`](./build-spec.md).
