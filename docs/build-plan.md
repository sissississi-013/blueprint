# P&ID Copilot — Comprehensive Build Plan

> **The actionable engineering plan.** This is the *how* — concrete file structure, data contracts, module signatures, rule implementations, configs, and an hour-by-hour execution plan. It implements the product defined in [`demo-spec.md`](./demo-spec.md) (governing/product shape) using the technical detail in [`build-spec.md`](./build-spec.md) (datasets, model IDs, rules). Read those two first; this turns them into code.

---

## 0b. Pre-flight & de-risking (post-review — READ FIRST)

Decisions adopted after a hard pre-event review. These override anything older in this doc.

**Three things that could sink the demo — handle first:**
1. **Invert loop ownership: Python owns the autonomy heartbeat; OpenClaw is the agent face.** A Python file-watcher (watchdog/polling on `/sandbox/revisions/`) drives ingest→validate→annotate→alert. OpenClaw hosts the session, routes Q&A/narration, and posts via NemoClaw's Telegram bridge — still genuine, scored stack use, but if OpenClaw's trigger is flaky you lose *narration, not autonomy*. (~40% of the score rode on the riskiest, never-run component; this removes that.) Implemented in `pidcopilot/server.py` (watcher) + `agent/` (OpenClaw face).
2. **Verify the demo graph PRE-DAY (at home), not at H2.5.** R1–R4 need a graph that actually contains a vessel, a PSV, a flare/disposal, a control valve, and a level instrument. Run `scripts/verify_dexpi.py` on pyDEXPI's C01 *on the Mac*. If C01 is too thin, fall back to `pidcopilot/demo/synthetic.py` (a hand-built graph guaranteed to contain exactly what the four rules need). **The demo backbone is the synthetic graph, so it never depends on C01 parsing.**
3. **MacBook validation ≠ GB10 validation.** Ollama serving an MoE GGUF on sm_121, NemoClaw, the draw.io AppImage, OpenShell localhost reachability — only truly proven on GB10/DGX Spark. Pre-test the exact serve command on ARM if possible; prefer the official `ollama run nemotron-3-nano` tag over a first-try Unsloth GGUF import. **Get hardware pre-access if at all possible.**

**Scope cuts (buy back hours):**
- **Cut diff-as-scoping.** At 30–200 nodes × ~3 ms/rule, a full re-scan per revision is microseconds. `diff.py` is kept **only** for regression messaging ("PSV-101 removed"), not for validation scoping. "We support incremental for large sheets" is a *talking point*, not code.
- **Decouple the dramatic finding from the reliable fix.** Lead the *finding* with R1 (the scary missing relief valve), but make the **one-click accept-fix money shot ride on R3 (set `fail_position=FC`) or R2 (rename duplicate)** — bulletproof value-fixes. R1's add-subgraph fix is shown as the *impressive bonus*. The "watch it fix itself" beat must not be able to break.
- **draw.io live-edit = bonus only; protect [A]'s time.** The scripted file-drop already tells the invisibility story. Do **not** let the agent person verify draw.io ARM/offline/compression in H1–2.5 while NemoClaw is the actual fire.
- **Confirm OpenClaw config-based tool registration before hand-writing TS skills.** If it can register HTTP/MCP-style tools from config, skip the TS layer and the extra contract entirely.

**Five-minute correctness nits (baked into the code):**
- **Tag regex loosened** to allow prefixes/suffixes: `^(\d+-)?([A-Z])([A-Z]*)-?(\d+)([A-Z])?$` (handles `PSV-101A`, `10-PSV-101`). Normalize before matching.
- **R1 with no flare node:** imply a disposal sink too (ghost flare) and/or flag "no disposal system" separately — never throw on a missing target.
- **Defensible passing count:** report `checks_run / passing / issues` with a **stable denominator**, not a number that jumps oddly between revisions.
- **Telegram zero-egress wording:** only a **terse notification** leaves the box (to `api.telegram.org`); **diagram content/IP never leaves** and is kept out of the alert text. Prefer the pane's **local alert feed** as the primary on-stage surface so the claim is airtight.

---

## 0. What we are building (one paragraph)

An **always-on P&ID Copilot** that runs entirely on the Dell GB10: it watches the P&ID revisions an engineer saves (in their own tool), converts each into a graph via an `ingest()` adapter, runs a **deterministic rule engine** that flags safety/compliance violations and draws **ghost edges** for what *should* exist, renders the result live on a **review pane** (Cytoscape.js), and uses a **local Nemotron model (via NemoClaw)** purely to *narrate* findings and answer graph Q&A. The whole agent is sandboxed by **OpenShell** (default-deny egress), and **NemoClaw's Telegram bridge** posts delta alerts. Nothing leaves the box; nothing about the engineer's workflow changes.

---

## 1. Locked decisions (do not relitigate mid-build)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Graph-first core and build order.** | Graph datasets are reasoning-ready; vision is a borrowable boundary adapter we can't build well in a day. (See `demo-spec.md` invisibility section.) |
| D2 | **Deterministic rule engine produces all findings; the LLM only narrates.** | Credibility + "can't hallucinate a safety pass" + works even if inference is slow. |
| D3 | **Overlay, not editor.** The pane renders THEIR revision; scripted buttons stand in for "engineer saved a new revision." | Invisibility principle. |
| D4 | **DEXPI is the rule-bearing substrate; PID2Graph `.graphml` is for visual realism.** | See §2 — only DEXPI carries the tags/types the rules need. |
| D5 | **Nemotron Nano-30B (Ollama) for reasoning/narration; Nano-12B-VL for the vision adapter only. Skip Super-120B.** | Bandwidth-bound box; Nano is fast enough and co-fits. |
| D6 | **All three stack components are load-bearing: OpenClaw (agent+tools+loop), NemoClaw (inference+Telegram), OpenShell (sandbox).** No bare-bridge bypass in the demo. | Rubric scores correct stack use (10%) + the security narrative (30% business). |
| D7 | **Python is the brain (ingest/graph/rules/diff/loop/websocket); OpenClaw skills are thin HTTP wrappers to it.** | Rule engine is Python (NetworkX/VF2); keeps OpenClaw orchestrating without porting graph logic to TS. |
| D8 | **"Suggest-the-fix" is our only generation: a rule fires → emit the corrective subgraph/value → one-click accept. NO from-scratch P&ID generation.** | Validation is a *subset* of generation; full generation adds a generative model + layout + hides the trust problem, and it's maximally "switch-y" (violates invisibility). Suggest-the-fix is the *same engine reversed* (Schweidtmann autocorrection, arXiv 2502.18493): generation's wow with validation's trust. |
| D9 | **Scope to four demo-critical rules: R1 relief path, R2 duplicate tag, R3 fail position, R4 level instrument.** R5/R6 are stretch. | The felt "overcomplication" is the 33-rule pile, not the problem. Four rules demo beautifully; two of them (R1, R4) drive the one-click-fix money shot. |

---

## 2. The substrate decision (critical — read before coding rules)

The 6 rules all need **rich per-node attributes**: instrument tag strings (`PT-101`, `PSV-101`), fine equipment subtypes (vessel vs PSV vs control valve), fail positions (FO/FC/FL), and connectivity with directionality. Where do those attributes actually exist?

| Source | Format | Carries tags? | Carries fine types? | Use it for |
|---|---|---|---|---|
| **DEXPI** (pyDEXPI) | Proteus `.xml` → rich object model → NetworkX | **Yes** (full smart-P&ID) | **Yes** (Pump, Vessel, PSV, ControlValve, nozzles…) | **The rule-bearing working diagram + the known-bad demo case.** This is where rules actually fire. |
| **PID2Graph** | `.graphml` | No (no tag text) | **No** — only 7 coarse classes (General, Pump/Compressor, Tank/Vessel, Instrumentation, Valve, Arrow, Inlet/Outlet) + 2 line classes | **Visual realism** ("here's a real OPEN100 sheet") and graph-diff/ingest plumbing tests. Rules degrade to topology-only on it. |
| **Synthetic (pyDEXPI generator)** | generated DEXPI | Yes | Yes | Fabricating clean + deliberately-broken demo P&IDs with full control. |
| **draw.io** (live demo input surface) | `.drawio` = mxGraph XML | **Yes** (via shape `tag` label) | **Yes** (via shape `type` data attr in our custom stencil) | **The live edit→save→review demo beat.** Deterministic XML parse, NOT vision. Presenter edits here on stage. |

**Consequence for the build:**
- The **canonical internal graph schema** (§4.1) is the single representation everything else targets. The DEXPI adapter populates it fully; the graphml adapter populates what it can (topology + coarse class) and leaves rule-required attrs `None`.
- Each rule **declares the attributes it requires** and **skips (does not false-flag)** nodes lacking them. So on a graphml-only graph, tag-grammar rules simply find nothing to check; on a DEXPI graph they fire fully.
- **Demo working diagram = a DEXPI P&ID** (pyDEXPI's `C01` reference, or a synthetic one) so all 6 rules visibly fire. Optionally render an OPEN100 graphml sheet alongside for the "real diagram" credibility beat, clearly framed as topology-only.

> If time is tight, the demo can run **entirely on DEXPI/synthetic graphs** and still hit every rubric point. PID2Graph is a "nice realism garnish," not a dependency.

---

## 3. Tech stack & repository structure

**Backend (the brain):** Python 3.11 · FastAPI + Uvicorn (HTTP + WebSocket) · NetworkX (graph + VF2 isomorphism) · Pydantic (data contracts) · pyDEXPI (DEXPI parse + synthetic gen) · `lxml` (Proteus XML).
**Frontend (the pane):** single static page, **Cytoscape.js** (vendored, no build step) + vanilla JS WebSocket client. Deliberately no framework/bundler — removes the #1 day-of risk.
**Agent:** OpenClaw (gateway + skills) on the **NemoClaw** reference stack; **Nemotron Nano-30B** served locally via Ollama; OpenClaw skills are thin TS/HTTP wrappers calling the Python service. **OpenShell** sandboxes the lot.
**Vision adapter (stretch):** Nemotron **Nano-12B-VL** via Ollama/vLLM for PDF/image → graph.

```
blueprint/
├── docs/                          # specs + this plan
├── pidcopilot/                    # Python package (the brain)
│   ├── __init__.py
│   ├── server.py                  # FastAPI app: HTTP endpoints + WebSocket hub
│   ├── config.py                  # paths, ports, model names, sandbox dirs
│   ├── graph/
│   │   ├── schema.py              # canonical Node/Edge/PidGraph pydantic + nx helpers
│   │   ├── normalize.py           # map adapter output -> canonical schema
│   │   └── diff.py                # diff(G, G') -> changed node/edge ids + affected neighborhood
│   ├── ingest/
│   │   ├── base.py                # IngestAdapter protocol; ingest(artifact) dispatcher
│   │   ├── graphml_adapter.py     # PID2Graph .graphml  (nx.read_graphml)
│   │   ├── dexpi_adapter.py       # DEXPI .xml via pyDEXPI  (PRIMARY rule-bearing)
│   │   ├── drawio_adapter.py      # .drawio mxGraph XML -> graph (LIVE DEMO surface, deterministic)
│   │   └── vision_adapter.py      # PDF/image -> graph via Nano-12B-VL (STRETCH)
│   ├── rules/
│   │   ├── engine.py              # RuleEngine.run(graph, scope) -> [Finding]; incremental
│   │   ├── base.py                # Rule protocol; Finding model; severity enum; registry
│   │   ├── r1_relief_path.py      # API 521 reachability + ghost edge
│   │   ├── r2_duplicate_tag.py
│   │   ├── r3_fail_position.py
│   │   ├── r4_level_instrument.py # VF2 pattern (Schulze Balhorn Rule 9)
│   │   ├── r5_pump_protection.py  # VF2 patterns (Rules 10/19/21)
│   │   └── r6_isa51_tag.py        # tag-grammar regex
│   ├── agent/
│   │   ├── tools.py               # callable funcs behind OpenClaw skills (HTTP handlers)
│   │   └── prompts.py             # narration + Q&A prompt templates (LLM never authors findings)
│   ├── alerts/
│   │   └── telegram.py            # format delta -> NemoClaw Telegram bridge call
│   ├── llm/
│   │   └── nemotron.py            # thin client -> NemoClaw/Ollama (narrate, qa)
│   └── demo/
│       ├── make_broken.py         # pyDEXPI: clean P&ID -> inject missing PSV + dup tag + strip FO
│       └── revisions.py           # scripted "saved revision" sequence for the demo
├── web/
│   ├── index.html                 # review pane
│   ├── pane.js                    # cytoscape init, ws client, annotation applier
│   ├── style.css                  # red/amber/green + ghost-edge styling
│   └── vendor/cytoscape.min.js
├── openclaw/
│   ├── skills/                    # pid-review skill(s): ingest, validate, explain, diff (TS/md)
│   └── openclaw.json              # agent config (model = nemotron-3-nano via NemoClaw)
├── deploy/
│   ├── openshell-policy.yaml      # default-deny egress; allow localhost:{8000,11434} + Telegram
│   └── nemoclaw-onboard.md        # exact onboard steps/answers
├── drawio/
│   ├── pid-stencil.xml            # custom draw.io library: shapes carry type+tag data attrs
│   ├── demo.drawio                # the clean demo P&ID (uncompressed XML) the presenter edits
│   └── README.md                  # how to load the stencil + save-uncompressed setting
├── fixtures/                      # frozen demo graphs (clean + broken), the one demo PDF
├── tests/                         # rule unit tests on tiny hand-built graphs
├── requirements.txt
└── run.sh                         # boot: ollama + python server + open pane
```

---

## 4. Data contracts (the spine — agree these first, build in parallel after)

### 4.1 Canonical graph schema (`pidcopilot/graph/schema.py`)
Every adapter outputs this; every rule reads this; the pane renders this.

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class NodeType(str, Enum):
    VESSEL = "vessel"; PUMP = "pump"; COMPRESSOR = "compressor"
    CONTROL_VALVE = "control_valve"; BLOCK_VALVE = "block_valve"; CHECK_VALVE = "check_valve"
    PSV = "psv"; RUPTURE_DISC = "rupture_disc"; STRAINER = "strainer"
    INSTRUMENT = "instrument"; FLARE = "flare"; DISPOSAL = "disposal"
    INLET = "inlet"; OUTLET = "outlet"; GENERIC = "generic"; UNKNOWN = "unknown"

class Node(BaseModel):
    id: str                       # stable id (DEXPI component id or graphml node id)
    type: NodeType
    tag: Optional[str] = None     # e.g. "PSV-101"  (None if source carries no tag)
    label: Optional[str] = None   # display text
    fail_position: Optional[str] = None     # "FO" | "FC" | "FL"  (control valves)
    measured_var: Optional[str] = None       # ISA first-letter, derived from tag
    bbox: Optional[tuple] = None  # (xmin, ymin, xmax, ymax) for layout if present
    attrs: dict = {}              # passthrough (line_no, service, set_pressure, ...)
    source_fidelity: str = "rich" # "rich" (DEXPI) | "topology" (graphml) — rules gate on this

class Edge(BaseModel):
    id: str
    source: str                   # Node.id
    target: str                   # Node.id
    kind: str = "process"         # "process" | "signal" | "instrument"
    directed: bool = True
    attrs: dict = {}

# In memory we use a networkx.DiGraph G with G.nodes[id]["data"]=Node, G.edges[...]["data"]=Edge.
# PidGraph wraps it with revision metadata.
class PidGraph(BaseModel):
    revision: int
    source: str                   # "dexpi" | "graphml" | "vision"
    nodes: list[Node]
    edges: list[Edge]
```

### 4.2 Finding (punch-list item) — the rule engine's output (`rules/base.py`)
```python
class Severity(str, Enum):
    RED = "red"        # mandatory / safety-critical (API 521, IEC 61511, mandatory rules)
    AMBER = "amber"    # suggested / non-blocking
    GREEN = "green"    # informational / passing marker

class GhostEdge(BaseModel):       # the "what SHOULD exist" overlay
    source: str
    target: Optional[str] = None  # None => target is a missing/implied node
    implied_node: Optional[Node] = None
    style: str = "ghost"

class ProposedFix(BaseModel):     # SUGGEST-THE-FIX: the corrective delta, one-click acceptable
    kind: str                     # "add_subgraph" (missing-component) | "set_attr" | "rename"
    summary: str                  # "Add PSV-101 and route to flare F-1"
    add_nodes: list[Node] = []    # promoted from the ghost (implied) nodes -> real
    add_edges: list[Edge] = []    # the relief routing, etc.
    set_attrs: dict = {}          # {node_id: {"fail_position": "FC"}}  for attribute fixes
    rename: dict = {}             # {node_id: "PT-102"}                 for duplicate-tag fixes

class Finding(BaseModel):
    rule_id: str                  # "R1" ... "R4" (R5/R6 stretch)
    severity: Severity
    node_ids: list[str]           # offending node(s) to highlight
    edge_ids: list[str] = []
    message: str                  # short, human: "V-101 has no relief path to flare"
    standard_ref: str             # "API 521 §5" | "ISA-5.1" | "IEC 61511"
    ghost_edges: list[GhostEdge] = []
    matched_subgraph: list[str] = []   # node ids of the VF2 match (for the highlight beat)
    fix: Optional[ProposedFix] = None  # SUGGEST-THE-FIX: present when the rule knows the correction
    explanation: Optional[str] = None  # filled in lazily by the LLM, on demand
```

### 4.3 WebSocket protocol (server ↔ pane)
JSON messages, both directions, over `ws://localhost:8000/ws`.

```
# server -> pane
{ "type": "graph",      "graph": <PidGraph> }                      # full render (on connect / new diagram)
{ "type": "annotations","revision": 7, "findings": [<Finding>],    # apply red/amber/ghost/badges
                        "passing": 47 }
{ "type": "highlight",  "node_ids": [...], "subgraph": [...] }      # Q&A glow / subgraph-match beat
{ "type": "explanation","rule_id": "R1", "text": "..." }           # async narration arrives

# pane -> server  (demo control + Q&A + fix)
{ "type": "apply_revision", "name": "delete_psv_101" }             # scripted "engineer saved a revision"
{ "type": "ask", "text": "which vessels have relief protection?" } # natural-language Q&A
{ "type": "why", "rule_id": "R1" }                                 # request explanation for a finding
{ "type": "accept_fix", "rule_id": "R1", "node_ids": ["V-101"] }   # SUGGEST-THE-FIX one-click accept
```

When `accept_fix` arrives, the server applies the `ProposedFix` to the graph as a **new revision**, re-validates, and pushes a fresh `graph` + `annotations`: the ghost PSV becomes a **real** node, the finding clears, and the green "passing" count ticks up. That round-trip *is* the generative money shot.

### 4.4 `ingest()` dispatcher (`ingest/base.py`)
```python
def ingest(artifact: str | bytes, hint: str | None = None) -> PidGraph:
    """Route by extension/sniff: .xml->dexpi, .graphml->graphml, .pdf/.png/.jpg->vision.
    Always returns a canonical PidGraph. Adapters never raise into the loop —
    on failure they return an empty graph + a surfaced error annotation."""
```
HTTP surface (FastAPI, all localhost):
- `POST /ingest` (multipart file | path) → `{revision, graph}`
- `POST /validate` `{revision, scope?}` → `{findings, passing}`
- `POST /revision` `{name}` (demo) → applies a scripted mutation, triggers loop
- `POST /explain` `{rule_id}` → `{text}` (calls LLM)
- `POST /ask` `{text}` → `{answer, highlight_node_ids}`
- `POST /accept_fix` `{rule_id, node_ids}` → applies `ProposedFix` as a new revision → `{revision, graph, findings, passing}`
- `GET  /health` → stack readiness (ollama up, model loaded, graph loaded)

---

## 5. The rule engine (the deterministic core — highest priority code)

### 5.1 Engine (`rules/engine.py`)
```python
class RuleEngine:
    def __init__(self, rules: list[Rule]): ...
    def run(self, G: nx.DiGraph, scope: set[str] | None = None) -> list[Finding]:
        """scope=None -> full graph (first load). scope={node_ids} -> incremental:
        only re-run rules whose 'touches' intersect the affected neighborhood (diff output).
        Each rule self-skips nodes lacking required attrs (source_fidelity gating)."""
    def passing_count(self, G, findings) -> int: ...   # for the green "N checks passing" overlay
```
Each `Rule` declares `requires: set[str]` (e.g. `{"tag"}`, `{"fail_position"}`) and `touches(node) -> bool` so incremental validation only reruns relevant rules. Determinism + sub-ms VF2 (paper: ~3.2 ms/rule) means a full re-scan is also cheap — incremental is for the "technical depth" story and large sheets. **Each rule also returns its `ProposedFix`** (see §5.4) so the engine and the suggest-the-fix layer are one and the same.

### 5.2 The four demo-critical rules (concrete logic + visual + fix) — D9
> Scope is **four rules**. R1 + R4 are *missing-component* rules → corrective **subgraph** (ghost → one-click accept), the money shots. R2 + R3 → corrective **value**. R5/R6 are stretch (§5.3).
>
> **Keep the ISA-5.1 tag parser as a shared util** (derives `measured_var` from a tag's first letter) — R4 needs it to find "level" instruments — even though R6-as-a-surfaced-finding is now stretch.

**R1 — Vessel has no relief path (API 521) · RED · LEAD WITH THIS. [missing-component → subgraph fix]**
- Required attrs: node types (`vessel`, `psv`/`rupture_disc`, `flare`/`disposal`).
- Logic: for each `VESSEL`, search (BFS over process edges, ignoring direction through valves) for a path `vessel → … → (PSV|RUPTURE_DISC) → … → (FLARE|DISPOSAL)`. If none: **Finding(RED)**.
- **Ghost edge:** `GhostEdge(source=vessel, implied_node=Node(type=PSV, label="PSV (missing)"))` + dashed edge to the nearest flare/disposal — the dramatic "draw the missing thing" beat.
- **Fix:** `ProposedFix(kind="add_subgraph", summary="Add PSV-<n> on V-101 and route to flare F-1", add_nodes=[<PSV>], add_edges=[vessel→PSV, PSV→flare])`. Accept → ghost becomes real → R1 clears.

**R2 — Duplicate instrument tag · RED. [value fix]**
- Required: `tag`. Logic: group nodes by normalized `tag`; any group size > 1 → Finding(RED) listing all offenders; `matched_subgraph` = the duplicate set (pane links them with a "duplicate" badge).
- **Fix:** `ProposedFix(kind="rename", summary="Rename the second PT-101 to PT-102", rename={dup_node_id: <next free loop number for that variable>})`.

**R3 — Control valve missing fail position · AMBER. [value fix]**
- Required: `type==control_valve`. Logic: if `fail_position not in {FO,FC,FL}` → Finding(AMBER); amber node.
- **Fix:** `ProposedFix(kind="set_attr", summary="Set FV-203 fail position to FC (fail-closed)", set_attrs={cv_id: {"fail_position": "FC"}})`. Default to **FC** (conservative/safe) and say so.

**R4 — Vessel missing level instrument (Schulze Balhorn Rule 9, mandatory) · RED. [missing-component → subgraph fix]**
- Required: vessel + instrument types/tags. Logic (VF2): pattern = a `VESSEL` with an adjacent `INSTRUMENT` whose `measured_var == "L"` (level). If no match for a given vessel → missing → Finding(RED). Use `nx.algorithms.isomorphism` subgraph matcher on `type`/`measured_var`.
- **Fix:** `ProposedFix(kind="add_subgraph", summary="Add level instrument LIT-<n> on V-101", add_nodes=[<LIT>], add_edges=[vessel→LIT])`.

### 5.3 Stretch rules (only if green by H8.5)
- **R5 — Pump protection set (Rules 10/19/21):** discharge `CHECK_VALVE` (19), suction `STRAINER` (10), block valves + drain (21); each missing → AMBER + ghost component + subgraph fix. Orientation via edge direction. Rule order matters (apply 21 before 10/19).
- **R6 — ISA-5.1 tag grammar:** regex `^([A-Z])([A-Z]*)-?(\d+)$`; first-letter ∈ measured-variable set, succeeding letters ∈ function set, loop number present. (Its **parser is already a shared util** used by R4.)
- PSV isolatable by a closed block valve (API 520/521); SIS/BPCS separation (IEC 61511); dangling/orphan nodes (works even on topology-only graphs).

### 5.4 Suggest-the-fix — generation as the engine reversed (the wow layer, D8)
Validation and generation are **the same engine pointed in opposite directions**: the rule that *detects* "V-101 has no relief path" already computes the corrective subgraph it would *add*. So each rule returns a `ProposedFix` alongside its `Finding` (§4.2). This is the Schweidtmann autocorrection pattern (arXiv 2502.18493) — and the only "generation" we do. **No from-scratch P&ID synthesis** (it's a superset of validation, needs a generative model + layout, and is maximally switch-y — see D8).

Flow:
```
rule fires -> Finding{..., ghost_edges, fix: ProposedFix}
   pane shows the red-line + the ghost (the "what should exist")
   + an [Accept fix] affordance on the finding
user clicks Accept -> {type:"accept_fix", rule_id, node_ids}
   server: apply fix to graph (promote ghost nodes->real, add edges / set attr / rename)
           -> NEW revision -> re-validate -> push {graph, annotations, passing}
   result: ghost PSV becomes REAL, finding clears, green "passing" count ticks up
```
**Why this is the right kind of generation:** it's a *suggestion you accept* (autocomplete-style), not an imposition — trustworthy (deterministic, standard-cited), invisible (no new authoring behavior), and it's the demo money shot. `apply_fix(graph, fix) -> graph'` lives in `rules/engine.py` (or `graph/` ) and is pure/deterministic.

### 5.5 Rule output → annotation mapping (server)
On each validate, server sends `{type:"annotations", findings, passing}`. The pane maps: `severity→node class` (red/amber), `ghost_edges→dashed ghost elements (+ implied nodes)`, `matched_subgraph→"matched" class on demand`, duplicate sets → badge, and **`fix` present → an [Accept fix] button on the finding callout.**

---

## 6. Ingest adapters

### 6.1 `graphml_adapter.py` (plumbing + visual realism)
```python
def load_graphml(path) -> PidGraph:
    g = nx.read_graphml(path)
    # map PID2Graph 7 classes -> coarse NodeType (Tank/Vessel->VESSEL, Valve->BLOCK_VALVE,
    # Instrumentation->INSTRUMENT, Pump/Compressor->PUMP, ...); tag=None; source_fidelity="topology"
    # edges: Solid->process, Non-Solid->signal. Carry bbox for layout.
```
Rules requiring `tag`/`fail_position` self-skip on these nodes (no false positives). Used to prove ingest+diff+render on a *real* sheet.

### 6.2 `dexpi_adapter.py` (PRIMARY — rule-bearing)
```python
def load_dexpi(path) -> PidGraph:
    model = pydexpi.loaders.proteus.parse(path)        # pyDEXPI Proteus import
    nxg = pydexpi.toolkits.to_networkx(model)          # rich graph
    # map DEXPI classes -> NodeType (Vessel, CentrifugalPump, SafetyValve->PSV,
    #   ControlValve w/ failAction->fail_position, ProcessInstrument->INSTRUMENT, Flare->FLARE)
    # tag = component TagName; attrs carry nozzles, set_pressure, line numbers; source_fidelity="rich"
```
Targets pyDEXPI's `C01V04-VER.EX01.xml` reference and synthetic outputs. **Verify pyDEXPI's exact API names on-site** (parser entrypoint + networkx export) — they're the one external API we depend on.

### 6.3 `drawio_adapter.py` (LIVE DEMO surface — deterministic, NOT vision)
```python
def load_drawio(path) -> PidGraph:
    # .drawio = mxGraph XML. Parse <mxCell> elements:
    #   vertices (vertex="1")  -> Node; edges (edge="1", source/target) -> Edge
    #   read type+tag from shape DATA: drawio stores custom data as a wrapping
    #     <object label=.. type=.. tag=..><mxCell .../></object>  (our stencil sets these)
    #   fall back to deriving type from the label/tag via ISA-5.1 grammar (R6) if data absent
    # source_fidelity="rich" (our stencil guarantees type+tag)
```
**Critical setup (in `drawio/README.md`):**
- **Save uncompressed:** draw.io compresses `<diagram>` (base64+deflate) by default. Disable via *Extras → Settings → uncheck "Compressed"* (or use the desktop `--disable-compression`) so the adapter reads plain XML. Otherwise decode deflate in the adapter.
- **Custom stencil** (`pid-stencil.xml`): one shape each for PSV, Vessel, Pump, Control Valve, Block Valve, Check Valve, Strainer, Flare, Instrument — each pre-seeded with `type` data and a `tag` placeholder. Presenter drags, sets the tag label, connects. This makes the parse deterministic and the drawing trivial.
- **Integration:** draw.io desktop/offline saves the `.drawio` file into the agent's watched folder (`/sandbox/revisions/`); Ctrl+S = "engineer saved a revision." Same file-watch path as every other adapter.
- **Local-first:** serve draw.io offline on the box (static webapp or desktop AppImage). **Verify ARM/offline on-site (§16).** If it won't run offline on the box, run it in the box's browser from a locally-served copy; do not use the public cloud page (breaks the no-egress story).

### 6.4 `vision_adapter.py` (STRETCH — invisibility proof)
```python
def load_vision(path) -> PidGraph:
    # 1) if PDF has embedded text/vector -> extract symbols+text deterministically first
    # 2) else: render page -> Nano-12B-VL prompt -> structured JSON {symbols:[{type,tag,bbox}], lines:[{a,b}]}
    # 3) build canonical graph; source_fidelity="rich" if confident else "topology"
```
Goal: ONE hand-checked PDF round-trips to a review. Accuracy is not graded; the *gesture* is. Keep a frozen fallback graph for this PDF in `fixtures/`.

---

## 7. Demo harness (`pidcopilot/demo/`)

### 7.1 `make_broken.py`
Start from a clean DEXPI/synthetic P&ID; produce a sequence of revisions by graph mutation:
- `delete_psv_101` → remove the PSV node + its edges (triggers R1 + its ghost edge).
- `duplicate_tag` → set a second node's tag to `PT-101` (triggers R2).
- `strip_fail_position` → null a control valve's `fail_position` (triggers R3).
Each returns the new `PidGraph` (revision n+1). These are the "engineer saved a revision" events.

### 7.2 `revisions.py`
Ordered list the pane's buttons invoke via `POST /revision {name}`. Deterministic, rehearsable, owns the demo beat.

---

## 8. Agent layer — OpenClaw + NemoClaw + OpenShell (the load-bearing stack)

### 8.1 Division of responsibility
- **Python service** = deterministic brain (ingest, graph, rules, diff, websocket, demo). Owns *findings*.
- **OpenClaw** = the agent/orchestrator. Hosts the always-on session, exposes **skills** (tools) that HTTP-call the Python service, runs the **trigger** that watches for new revisions, and routes narration/Q&A turns to the model. Owns *conversation + autonomy loop*.
- **NemoClaw** = serves **Nemotron Nano-30B** locally (Ollama provider) and provides the **Telegram bridge** for delta alerts.
- **OpenShell** = sandbox around the whole thing; default-deny egress, allow only localhost + Telegram.

### 8.2 OpenClaw skills (`openclaw/skills/` — thin TS/HTTP wrappers, no graph logic)
| Skill / tool | Calls | Returns to agent |
|---|---|---|
| `ingest_revision(path)` | `POST /ingest` | revision id, node/edge counts |
| `validate(revision, scope?)` | `POST /validate` | findings (rule_id, severity, message, standard_ref) |
| `diff_revisions(a,b)` | `POST` diff | changed components + regressions ("PSV-101 removed") |
| `explain_finding(rule_id)` | `POST /explain` | passes finding context to model; returns narration |
| `accept_fix(rule_id, node_ids)` | `POST /accept_fix` | applies the `ProposedFix` → new revision → cleared finding (suggest-the-fix) |
| `ask_graph(question)` | `POST /ask` | answer + node ids to highlight |

The **always-on trigger**: an OpenClaw scheduled/file-watch skill watches `/sandbox/revisions/`; a new file → `ingest_revision` → `validate` → if findings changed, `explain_finding` (async) + Telegram alert. In the demo the pane's button also drops a file there (or calls `/revision`), so the *same* path fires — autonomy is real, not faked.

### 8.3 `openclaw/openclaw.json` (sketch)
```json
{
  "gateway": { "port": 18789 },
  "agents": { "pid-reviewer": {
    "model": "nemoclaw:nemotron-3-nano",
    "skills": ["pid-review"],
    "system": "You narrate and answer questions about P&ID findings produced by the deterministic rule engine. You NEVER invent or override findings. If asked whether something passes, defer to validate()."
  }},
  "channels": { "telegram": { "enabled": true } }
}
```

### 8.4 `deploy/openshell-policy.yaml` (default-deny egress)
```yaml
egress:
  default: deny
  allow:
    - { host: "127.0.0.1", ports: [8000, 11434, 18789] }   # python svc, ollama, openclaw
    - { host: "api.telegram.org", ports: [443] }            # NemoClaw Telegram bridge ONLY
filesystem:
  read_write: ["/sandbox", "/tmp"]
  read_only:  ["/usr", "/lib", "/etc"]
```
> The blocked-egress story is a *pitch asset*: optionally demo OpenShell's TUI denying an unlisted destination to show "the agent physically cannot exfiltrate plant IP."

### 8.5 NemoClaw onboarding (`deploy/nemoclaw-onboard.md`)
`curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash` → `nemoclaw onboard` → choose **local Ollama** provider, model `nemotron-3-nano` → apply the OpenShell policy above → enable Telegram bridge (bot token from USB, not day-of) → `nemoclaw pid-reviewer connect`. Round-trip a "hello" before building anything else.

---

## 9. LLM prompt contracts (`agent/prompts.py`) — the model never authors findings

**Narration (`/explain`):** input = one `Finding` (JSON) + a 1-hop subgraph summary. Output = 2–3 sentences: what's wrong, why it matters, the standard. Hard constraint in system prompt: *"Explain the provided finding. Do not add, remove, or contradict findings. Do not claim anything passes."*

**Q&A (`/ask`):** GraphRAG-lite — the server runs the *deterministic* query on the graph (e.g. "vessels with relief protection" = R1 logic inverted) and passes the **result set** to the model only to phrase it; returns `highlight_node_ids` for the glow. The model never computes the answer from raw graph guessing — it phrases a computed result. Keeps it correct and on-box-fast.

**Model:** Nano-30B via NemoClaw/Ollama. Narration is **async + non-blocking**: red-lines (rule engine) render instantly; the "why" text streams in a beat later. Never put the model on the critical path of the red-line.

---

## 10. The continuous loop — end-to-end sequence

```
engineer saves revision  (demo: button -> POST /revision {name}, OR file dropped in /sandbox/revisions/)
  -> OpenClaw trigger fires  ->  ingest_revision()  ->  PidGraph G'
  -> server: diff(G, G') -> changed_ids, affected_neighborhood
  -> RuleEngine.run(G', scope=affected)  ->  findings'   (+ revision regressions vs G)
  -> server -> pane:  {type:"annotations", findings', passing}      (INSTANT red/amber/ghost)
  -> OpenClaw: if new RED finding -> Telegram alert (NemoClaw bridge)  ["Rev 7: PSV-101 removed -> V-101 violates API 521"]
  -> (async) explain_finding() streams narration -> pane callout + Telegram
  -> G := G'   (persist revision state for next diff)
```
Two independently-demoable halves: **(a)** rule engine → pane red-line (must work), **(b)** OpenClaw → Telegram + narration (the stack/autonomy proof). Build (a) first; (b) is wired once (a) is solid.

---

## 11. Pre-day checklist (do this on the MacBook → 64 GB USB)

Day-of internet is slow; arrive with everything. **Order by importance** (if the stick fills, drop from the bottom):
1. **Nemotron Nano-30B GGUF** (`unsloth/NVIDIA-Nemotron-3-Nano-30B-A3B-GGUF`, UD-Q4 ~24 GB) + the Ollama Modelfile/tag pre-pulled.
2. **PID2Graph.zip** (9.3 GB, Zenodo 14803338) + **pyDEXPI repo** (incl. `C01V04-VER.EX01.xml`).
3. **NemoClaw** install script + repo + **a tested `nemoclaw onboard` config** + **Telegram bot token** (created in advance).
4. **This repo** (`blueprint`) with `requirements.txt` and **Cytoscape.js vendored** (`web/vendor/`), plus a Python wheel cache (`pip download -r requirements.txt -d wheels/`).
5. **draw.io offline** (desktop AppImage for linux-arm64, *and* a locally-servable static webapp copy as backup) + our **`pid-stencil.xml`** custom library + **`demo.drawio`** (saved uncompressed). Pre-test loading the stencil and the save→watched-folder path.
6. **One real P&ID PDF** for the vision beat + its **frozen fallback graph** in `fixtures/`.
7. **Nano-12B-VL GGUF** (only if room) for the vision adapter.
8. Pre-built **fixtures**: clean DEXPI graph + the 3 broken revisions, generated and committed before the event.

Also pre-write `run.sh` and rehearse `nemoclaw.sh → onboard → Ollama provider` once on any Linux/ARM box if possible. **Do not plan to download the 120B on-site.**

---

## 12. Hour-by-hour execution plan (≈10 hr, team of 2–3)

**Parallelization key:** **[A]** = agent/stack person, **[E]** = engine/Python person, **[U]** = UI/pane person. With 2 people, A doubles on E.

| Block | [A] agent/stack | [E] engine/Python | [U] UI/pane | Exit criteria (gate) |
|---|---|---|---|---|
| **H0–1** | NemoClaw onboard, Ollama+Nano-30B, OpenShell policy, Telegram "hello" round-trip | `requirements` install from wheels; FastAPI skeleton + `/health` + WebSocket echo | Static pane loads, Cytoscape renders a hardcoded 3-node graph over WS | Telegram↔Nemotron works **and** pane shows a graph from the server |
| **H1–2.5** | OpenClaw skill stubs (HTTP wrappers) hitting `/health`,`/validate`; draw.io offline + stencil load verified | **`schema.py` + `dexpi_adapter` + `graphml_adapter` + `drawio_adapter`**; load C01 → canonical `PidGraph`; `diff.py` | Pane renders the real loaded graph; layout/labels readable | A real DEXPI graph **and** a `.drawio` save both render in the pane |
| **H2.5–5** | wire `validate`/`explain`/`accept_fix` skills; trigger that watches `/sandbox/revisions/` (catches draw.io saves + scripted drops) | **Rule engine + R1,R2,R3** (R1 ghost edge + `ProposedFix`!); `make_broken.py` revisions | annotation applier: red/amber classes, ghost-edge style, duplicate badge, "N passing" overlay, **[Accept fix] button** | Edit in draw.io + Ctrl+S → V-101 red + ghost edge in the pane (and the scripted-button path also works) |
| **H5–6** | Nemotron narration (`/explain`) + Q&A (`/ask`) via NemoClaw; Telegram delta alert on RED; **`apply_fix` → accept_fix round-trip** | **R4** (VF2 pattern) + `ProposedFix` for all four | "why?" click → callout; **Accept fix → ghost becomes real, finding clears, passing++**; Q&A glow; subgraph-match highlight | All 4 rules fire; **R1 Accept-fix money shot works**; Telegram pings on the break |
| **H6–7** | full continuous loop through OpenClaw (trigger→ingest→validate→alert); regression detection | incremental `scope` validation + revision state | polish red/amber/green, animations | The whole loop runs unprompted from a dropped revision file |
| **H7–8.5** | — | harden; unit tests on tiny graphs; freeze `fixtures/` | ghost-edge animation, subgraph highlight beat, green overlay count | Demo runs clean on frozen fixtures, no manual prodding |
| **H8.5–9.5** | help vision adapter routing/policy | **vision adapter**: one PDF → graph (Nano-12B-VL or detector) | render the vision-ingested graph identically | One real PDF round-trips to a review (or frozen fallback used) |
| **H9.5–10** | run book + Telegram on the projector | rehearse | rehearse | 5-min script run **3×** clean; fallbacks staged |

---

## 13. Testing & rehearsal

- **Rule unit tests** (`tests/`): hand-build 4–6 tiny `nx.DiGraph`s (vessel+PSV+flare passing; vessel-only failing; dup tags; CV without fail pos; pump w/o check valve). Assert exact `Finding` sets. These are the safety net that lets you refactor fast.
- **Golden demo run:** a script that replays the scripted revisions and asserts the expected findings appear — run before every rehearsal so a late change can't silently break the beat.
- **Rehearse the pitch, not just the code.** Demo+pitch is 30%. Time the 5-min script; assign who clicks, who talks, who watches Telegram on screen.

---

## 14. Fallback ladder (degrade gracefully, never go dark)

1. **Vision adapter flaky** → use the frozen fallback graph for the PDF beat; lean on DEXPI. (Doesn't touch the core.)
2. **draw.io live edit flaky** (offline/ARM/compression) → fall back to the **scripted "saved revision" buttons** in the pane, which drop the *same* pre-made `.drawio`/DEXPI files into the watched folder. Identical downstream; you lose only the live-drawing flourish. Keep these buttons wired and one keypress away at all times.
3. **OpenClaw trigger/file-watch flaky** → pane button calls `POST /revision` directly; trigger still demoed once if possible. Loop still visibly autonomous (no per-finding prompting).
4. **Telegram bridge down** → show alerts in the pane's alert feed; keep debugging NemoClaw (it's load-bearing) but don't block the demo.
5. **Cytoscape pane slips** → server renders annotated graph to PNG (NetworkX/Graphviz) and posts per revision (still invisible, less wow).
6. **Nemotron narration slow/unstable** → red-lines are deterministic and instant regardless; show canned-but-real explanations from the `Finding.message`/`standard_ref` (rule engine already produced them) and skip live LLM narration.
7. **NemoClaw fully broken** (last resort, not in scored demo) → bare `python-telegram-bot`; keep OpenShell as the security story. Avoid unless forced.

Rule: **the deterministic rule engine + pane red-line is the floor** — if only that works, you still have a real, on-box, visual safety catch.

---

## 15. Definition of done

**MVP (must have for a credible demo — protect these):**
- [ ] Nano-30B served locally via NemoClaw; Telegram round-trip works.
- [ ] DEXPI/`.graphml` ingest → canonical graph → pane render.
- [ ] Rules R1, R2, R3 firing; **R1 ghost edge** visible.
- [ ] Scripted "Delete PSV-101" revision (button → watched folder) → instant red-line + Telegram ping.
- [ ] **R1 Suggest-the-fix: [Accept] → ghost PSV becomes real → finding clears, passing++.** (The generative money shot.)
- [ ] Click-to-explain narration from Nemotron.
- [ ] 5-min script rehearsed on frozen fixtures.

**Target (the winning demo):** + **live draw.io edit → Ctrl+S → red-line** (the real edit→save beat) · **R4** + Accept-fix on all four · Q&A glow · subgraph-match highlight · revision-regression message · full OpenClaw continuous loop.

**Stretch (only if green by H8.5):** vision PDF/image ingest · OpenShell egress-block TUI beat · OPEN100 graphml realism sheet · **R5 pump-set / R6 ISA-grammar rules** · SIS/BPCS + PSV-isolation rules.

---

## 16. Open unknowns — verify on-site in H0–1, before committing code paths

1. **pyDEXPI exact API** (parser entrypoint + NetworkX export function names + how `failAction`/tags surface). Our DEXPI adapter depends on it — confirm against the installed version first thing.
2. **NemoClaw local-Ollama provider config + Telegram setup** in the current preview build (it's early-preview; APIs may have moved). Debug here, not at H6.
3. **Nano-30B tokens/sec on the actual GB10** for narration — confirm it's comfortably interactive; if not, shorten narration prompts / make fully async.
4. **Whether OPEN100 `.graphml` carries any usable tag/text** in the version you downloaded (if it does, R-rules degrade less on it). Assume not; treat as topology-only.
5. **OpenShell + browser localhost reachability** — confirm the pane (host browser) can hit the sandboxed service on the allowed localhost port.
6. **draw.io offline on ARM** — confirm the desktop AppImage (or locally-served static webapp) runs on DGX OS ARM with no network; confirm **save-uncompressed** is set and the `.drawio` lands in the watched folder; confirm the custom stencil loads and its `type`/`tag` data survive the round-trip. If any of this is shaky, default to the scripted-button fallback for the demo and treat live draw.io as a bonus.
