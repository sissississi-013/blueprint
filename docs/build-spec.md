# P&ID Reviewer — Full Spec & Build-Plan for the Dell × NVIDIA GB10 Hackathon

> **Deep implementation reference** (datasets, rule set, model IDs/serving). Refines [`project.md`](./project.md): the decision is firmly **graph-first, not vision-first**.
>
> **⚠️ Product shape is now governed by [`demo-spec.md`](./demo-spec.md)** — the "P&ID Copilot" continuous live-red-lining reframe. The "submit a file → punch-list" flow below is superseded by the continuous validation loop; the datasets, rule set, and Nemotron serving details here remain fully valid. See [`hackathon-context.md`](./hackathon-context.md) for rules/rubric and [`sponsor-tech-and-advantages.md`](./sponsor-tech-and-advantages.md) for the stack.

## TL;DR
- **Build it graph-first, not vision-first.** Skip detector training entirely: load PID2Graph `.graphml` ground-truth graphs (and/or pyDEXPI-parsed DEXPI P&IDs) into NetworkX, run a deterministic rule engine for the validation punch-list, and use a local NVIDIA Nemotron model as the "reviewer agent" that narrates findings and answers Q&A over Telegram/Slack via NemoClaw + OpenShell on the GB10.
- **The whole stack is locally runnable on one GB10.** Nemotron-3-Nano-30B-A3B (or Nano-12B-v2-VL for image ingest) runs interactively at usable speed; Nemotron-3-Super-120B-A12B fits in the 128 GB unified memory but throughput is contested (community llama.cpp builds report ~14 t/s, while DGX Spark forum users report 65+ tok/s with NVFP4/vLLM optimizations that currently hit Blackwell kernel bugs) — so treat Super-120B as a non-interactive "deep review" path. The rule set is grounded in real, public sources: ISA-5.1 tag grammar, API 520/521 relief rules, IEC 61511 SIS boundaries, and the 33 published rule-graph checks from Schulze Balhorn et al. (TU Delft Process Intelligence Research + Fluor BV, arXiv 2502.18493).
- **Pitch the business case hard:** P&ID review is a manual bottleneck inside a large engineering-software market (independent estimates put it at roughly $43–54B in 2025–26; Hexagon, AVEVA, Bentley, Autodesk and startups like Pathnovo all play here). An always-on, fully-local, audit-logged agent that catches missing relief paths, duplicate tags, and fail-position omissions before HAZOP is a concrete, on-prem, data-private enterprise win that shows off the Dell/NVIDIA stack.

## Key Findings

### Fastest path to a demo
The single biggest time-saver is to **not** do symbol/line detection from raster images on day one. Two public sources give you machine-readable connectivity graphs for free:
1. **PID2Graph** (`.graphml`, loads directly into NetworkX) — real-world OPEN100 reactor sheets + synthetic sheets.
2. **pyDEXPI** — parses DEXPI Proteus `.xml` smart-P&IDs into a NetworkX graph, and can even generate synthetic P&IDs.

On top of either graph you run a **deterministic rule engine** (the highest-value, most demoable, most judge-credible component) and then layer the Nemotron reviewer agent for narration + natural-language Q&A (GraphRAG-style). This de-risks the build: even if nothing else works, the rule engine over ground-truth graphs produces a real punch-list.

### Nemotron model selection for the GB10 (128 GB unified memory, 273 GB/s bandwidth)
The GB10's constraint is memory bandwidth, not capacity — token generation on large models is slow (Apertus.ai's DGX Spark review measured Llama 3.1 70B at ~2.7 tokens/sec). Choose models so interactivity lives on Nano-class models and bulk capacity (loading a 120B reasoner *and* a 12B VLM at once) is the headline advantage.

---

## Details

## 1. Datasets — exact download instructions

### 1.1 PID2Graph (PRIMARY — use this) — Stürmer, Graumann, Koch, IEEE DSAA 2025
- **arXiv:** 2411.13929 — https://arxiv.org/abs/2411.13929 (HTML: https://arxiv.org/html/2411.13929v2)
- **Zenodo record:** https://zenodo.org/records/14803338 — DOI 10.5281/zenodo.14803338
- **License:** CC BY-SA 4.0
- **Single download file:** `PID2Graph.zip`, **9.3 GB**, md5 `90f782220de97e7e249d2595c49ddc1c`
- **Download command:**

```bash
wget -O PID2Graph.zip "https://zenodo.org/records/14803338/files/PID2Graph.zip?download=1" && unzip PID2Graph.zip
```

- **Contents:**
  - **OPEN100 (real-world subset): 12 manually annotated public P&IDs** from the OPEN100 nuclear-reactor design (energyimpactcenter.org / open-100.com). Per the SynthPID paper (arXiv 2604.16513), this is "the only publicly available P&ID graph benchmark, comprising 12 real-world images from the OPEN100 nuclear reactor design… each image retains between 57 and 210 physical components and 28 to 118 edges." ~382±125 nodes / ~381±126 edges per plan when counting crossings/ankles. Notably contains **no dashed/non-solid lines**.
  - **Synthetic subset:** plans built from ISO-10628-based symbols (Baltakatei Sandoval 2023), ~131±14 nodes per plan, ~23,323 symbols total.
  - Organized into **Complete Plans** and **Patched Plans** (overlapping tiles), each with its own `.graphml`.
- **Annotation format:** nodes = symbols with bounding box `(xmin, ymin, xmax, ymax)` + label; edges = lines with label. Also `connector` nodes (symbol/line connection points) and `border-node`s (line leaving a patch). **7 symbol classes** (General, Pump/Compressor, Tank/Vessel, Instrumentation, Valve, Arrow, Inlet/Outlet) + **2 line classes** (Solid, Non-Solid).
- **Load into NetworkX:**

```python
import networkx as nx
G = nx.read_graphml("path/to/plan.graphml")
```

- Companion-paper benchmark (Relationformer, arXiv 2411.13929v2, on patched OPEN100): symbols 73.49%, nodes 82.18%, connections 76.79% — outperforming the modular baseline by >25% on edge detection.

### 1.2 Dataset-P&ID (Paliwal et al. 2021) — 500 synthetic P&IDs, 32 symbol classes
- **Paper:** arXiv 2109.03794 — https://arxiv.org/abs/2109.03794 (PAKDD 2021, Springer doi 10.1007/978-3-030-75015-2_17)
- **Original Google Drive:** https://drive.google.com/drive/u/1/folders/1gMm_YKBZtXB3qUKUpI-LF1HE_MgzwfeR
- **HuggingFace mirrors (easier for agents):**
  - YOLO format: https://huggingface.co/datasets/hamzas/digitize-pid-yolo
  - Symbols-only: https://huggingface.co/datasets/hamzas/digitize-pid-symbols
  - Download: `huggingface-cli download hamzas/digitize-pid-yolo --repo-type dataset --local-dir ./dataset-pid`
- **Format:** 500 P&IDs at 7168×4561 px; annotations for symbols, lines, words; train/val 4:1. License CC BY-SA 4.0. Symbols 1–25 are "complex" (structurally similar).

### 1.3 ASU PID_dataset (Gupta/Czerniawski) — Zenodo 8028570
- **Record:** https://zenodo.org/records/8028570 — DOI 10.5281/zenodo.8028570 — **License CC BY 4.0**
- Real industry + web-scraped P&IDs, includes code + trained weights. Paper: "Semi-supervised symbol detection for P&IDs," *Automation in Construction* 159 (2024) 105260, doi 10.1016/j.autcon.2023.105260. Repo: https://github.com/mgupta70/PID_Symbol_Detection (also a `PIDQA` Q&A dataset).

### 1.4 Kaggle pid-symbols (Hristov) — YOLOv5 symbols
- https://www.kaggle.com/datasets/hristohristov21/pid-symbols (`kaggle datasets download -d hristohristov21/pid-symbols`)
- Repo: https://github.com/ch-hristov/p-id-symbols ("YOLOv5 for symbol extraction in P&ID diagrams"). Also a Roboflow mirror: https://universe.roboflow.com/pid-connect/p-id-symbols

### 1.5 DEXPI sample P&IDs / training test cases
- **DEXPI TrainingTestCases:** https://gitlab.com/dexpi/TrainingTestCases — reference P&IDs incl. C01 (Proteus `.xml`). Used as ground-truth smart-P&IDs; parse with pyDEXPI.
- pyDEXPI ships the DEXPI reference P&ID `data/C01V04-VER.EX01.xml`.

### 1.6 SynthPID / synthetic generation
- Generate your own DEXPI synthetic P&IDs via **pyDEXPI**'s synthetic generation module (see §3). Useful for fabricating *known-bad* P&IDs (inject a missing PSV, a duplicate tag) for a crisp demo. (SynthPID itself: arXiv 2604.16513 — verify final venue/version given the 2026 ID.)

---

## 2. The exact rule set (concrete & checkable)

### 2.1 ISA-5.1 tag/identification grammar
- **Standard:** ANSI/ISA-5.1 (current: 2024, "Instrumentation and Control Symbols and Identification"; prior 2009/1984). Purchase: ISA. Free public summaries below.
- **Free letter-code references:**
  - EngineeringToolBox ISA codes: https://www.engineeringtoolbox.com/isa-intrumentation-codes-d_415.html
  - InstruNexus detailed analysis (full letter table + loop-numbering schemes): https://instrunexus.com/isa-5-1-instrumentation-symbols-and-identifications-detailed-analysis/
  - The ANSI/ISA-S5.1-1984(R1992) text is publicly mirrored online.
- **Grammar:** A tag = **functional identification** (letters) + **loop number**.
  - **First letter** = measured/initiating variable: A analysis, F flow, L level, P pressure, T temperature, S speed/frequency, W weight/force, V vibration, Z position, etc. (chosen by measured variable, not manipulated — a valve on a level loop is **LV**, not FV).
  - **Succeeding letters** = readout/passive + output functions: I indicate, R record, C control, T transmit, Y relay/compute/convert, Q totalize/integrate, G glass/gauge, A alarm, with modifiers H high, L low, D differential.
  - Examples: PT (pressure transmitter), FIC (flow indicating controller), LIT (level indicating transmitter), TAH (temp alarm high), TDAL (differential-temp alarm low). **PSV** = any valve protecting against emergency pressure; **PSE** = rupture disc.
  - **Loop numbering:** parallel (number reused per variable, e.g. TIC-101/PIC-101/LIC-101 share 101) or serial (unique). Loop number may encode plant-area; e.g. 900–999 reserved for safety.

### 2.2 Safety/relief standards (summarize + cite)
- **API 520 (sizing/selection) & API 521 (pressure-relieving & depressuring systems):** every pressure-protected vessel must have a relief path to a defined disposal point (flare/atmosphere/collection); PSV inlet line pressure drop ≤ **3%** of set pressure (API 520); PSV mounted vertical, free-draining; no isolation that can orphan a vessel from its PSV. Standard page: https://www.api.org/products-and-services/standards/important-standards-announcements/standard521
- **IEC 61511 (SIS):** the Safety Instrumented System must be **separated from the BPCS** logically and physically; SIS field devices tagged distinctly; SIL-rated loops identified.
- **ISA-5.1 line/signal conventions:** process line (solid), pneumatic (cross-hatched/double-slash), electric (dashed), hydraulic (long dash), capillary (X). Signal-line type must match instrument type.
- **Good free checklist sources:** iFluids P&ID review checklist (https://ifluids.com/blog/pid-review-checklist-design-hazop-operations/), instrumentationtools.com control-valve guidelines, piping-world.com complete P&ID guide.

### 2.3 Published rule-graph rules — Schulze Balhorn et al. (arXiv 2502.18493)
**33 engineering rules** ("we developed 33 rules based on chemical engineering knowledge and heuristics, with five selected rules demonstrated as examples") encoded as **rule graphs**, applied to a pyDEXPI NetworkX graph via **VF2 subgraph isomorphism** (NetworkX), extended with conditional constraints (ranges/sets/inequalities). Each rule carries: ID, milestone (issue-for-review/design/construction), revision description, explanation, recommendation level (mandatory/suggested/consideration), "missing-component" boolean, and source. Insertion = red, deletion = blue. Reported **100% accuracy** on the case-study graph, ~3.2 ms/rule (0.016 s total on the C01 reference P&ID graph of 33 nodes/36 edges). The 5 demonstrated rules (verbatim from Table 1):
1. **Rule 3 (suggested):** "Do not install a globe valve as a control valve if the pipe diameter is greater or equal to 100 DN (or 4")." (large globe valves cost more)
2. **Rule 9 (mandatory):** "Install a level instrument on a vessel." (prevent overflow accidents)
3. **Rule 10 (suggested):** "Install a strainer in the suction line of a pump." (protect pump from solids)
4. **Rule 19 (suggested):** "Install a check valve on a pump's discharge line to avoid backflow."
5. **Rule 21 (mandatory):** "Install block valves and a drain in the suction and discharge of a pump." (isolation for maintenance)

Implementation note: for "missing-component" rules, VF2 searches for *both* the erroneous and corrected patterns — if only the erroneous pattern matches, the component is missing and the graph manipulation (insert/delete) is applied. Rule order matters (apply Rule 21 before 10 and 19 so strainers/check valves land correctly).
- Paper PDF: https://arxiv.org/pdf/2502.18493

### 2.4 Concrete enumerated validation checks to implement (prioritized for the demo)
Tier A (highest demo impact, easy on a graph):
1. **Unique instrument tags** — flag duplicate tag IDs (cross-team duplication is the classic real-world error).
2. **ISA-5.1 tag grammar validation** — regex/grammar check first-letter ∈ valid measured-variable set, succeeding letters valid, loop number present.
3. **Every vessel/pressure equipment has a relief path** (API 521) — graph reachability from vessel node to a PSV/PSE then to a disposal sink.
4. **Every control valve has a defined fail position** (FO/FC/FL) — attribute presence check.
5. **Every vessel has a level instrument** (Rule 9, mandatory).
6. **Pump protection set** — check valve on discharge (Rule 19), strainer in suction (Rule 10), block valves + drain (Rule 21).

Tier B:
7. **Line-number consistency** — unique line number per equipment-to-equipment run; new number across material-class break.
8. **Signal-line/instrument-type consistency** (ISA-5.1).
9. **PSV not isolatable** — no closed block valve orphaning a PSV (API 520/521).
10. **SIS/BPCS separation** — SIS-tagged devices distinct from BPCS (IEC 61511).
11. **Globe-valve-as-control-valve on large line** (Rule 3).
12. **Dangling connections / orphan nodes** — graph integrity (lines to nowhere).

---

## 3. Agent-friendly resources

### 3.1 Detection / digitization / graph-extraction repos
| Repo | URL | What / framework | License / notes |
|---|---|---|---|
| Azure-Samples/digitization-of-piping-and-instrument-diagrams | https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams | full pipeline: AutoML symbol detect + Azure Doc Intelligence OCR + Hough line detect + graph construction; REST endpoints; 32-symbol set | ~116★, 44 forks; uses Dataset-P&ID; ~8–9 open issues; best end-to-end reference |
| ch-hristov/p-id-symbols | https://github.com/ch-hristov/p-id-symbols | YOLOv5 symbol extraction | + Kaggle dataset |
| mohdahmad242/PID-detection | https://github.com/mohdahmad242/PID-detection | Detectron2 detection + classification | |
| aneeshbhattacharya/Automated-PnID-Symbol-Detection-and-Labelling | https://github.com/aneeshbhattacharya/Automated-PnID-Symbol-Detection-and-Labelling | custom PyTorch symbol detect + EAST text + labelling; conda env (`python=3.7.13`) | 41★, 20 forks; needs EAST frozen model from Dropbox |
| mgupta70/PID_Symbol_Detection | https://github.com/mgupta70/PID_Symbol_Detection | semi-supervised symbol detection (Automation in Construction 2024) | + PIDQA Q&A set |
| heyad/Eng_Diagrams | https://github.com/heyad/Eng_Diagrams | engineering-diagram analysis | |
| Digitize-PID | per arXiv 2109.03794 | end-to-end detect pipes/symbols/text → graph | reference impl behind Dataset-P&ID |

### 3.2 Agentic frontier (P&ID + LLM)
- **ChatP&ID** (GraphRAG over DEXPI knowledge graphs): arXiv 2603.22528 — https://arxiv.org/pdf/2603.22528. Tested ContextRAG/VectorRAG/PathRAG/CypherRAG; **ContextRAG best accuracy + lowest cost + fastest**. Project: https://www.pi-research.org/project/chatpnid/
- **"Talking like P&IDs"**: arXiv 2502.18928 — high-level + complete knowledge graph → graph-RAG → LLM Q&A; built on pyDEXPI/Neo4j.
- **Rule-based autocorrection on graphs**: arXiv 2502.18493 (the 33 rules; see §2.3). PDF: https://arxiv.org/pdf/2502.18493
- **Sakhinana et al. (TCS Research) multi-agent RAG:**
  - 2409.00082 — hierarchical multi-agent RAG for P&ID/PFD VQA, on-prem, open small VLMs + ReAct (no public code located).
  - 2412.05937 — agentic web navigation + Graph-RAG for diagram generation.
  - 2412.12898 — agentic auto-creation of P&IDs from natural language.
- **pyDEXPI:** https://github.com/process-intelligence-research/pyDEXPI — Pydantic DEXPI data model, Proteus `.xml` import, NetworkX graph export, SVG export, synthetic P&ID generation. Install: `git clone https://github.com/process-intelligence-research/pyDEXPI && cd pyDEXPI && pip install .`

### 3.3 Tools/libraries
- **NetworkX** (graph + VF2 isomorphism `nx.algorithms.isomorphism`), **pyDEXPI** (DEXPI), **DEXPI/Proteus** schema (https://gitlab.com/dexpi), **GraphRAG** implementations, **YOLO / Detectron2** (detection if needed), local **OCR**: Tesseract, PaddleOCR, or the Nemotron Nano VL VLM's built-in OCR.

### 3.4 NVIDIA Nemotron models — exact IDs, downloads, serving

**Text reasoning agent (recommended interactive model): Nemotron-3-Nano-30B-A3B** (30B total, ~3.5B active, hybrid Mamba-2/MoE, 1M ctx)
- Ollama: `ollama run nemotron-3-nano` (also `ollama launch openclaw --model nemotron-3-nano`)
- HF GGUF (Unsloth): `hf download unsloth/NVIDIA-Nemotron-3-Nano-30B-A3B-GGUF --include "*UD-Q4_K_XL*"` (~24 GB RAM at 4-bit)

**Vision ingest (image P&IDs → OCR/tags): Nemotron-Nano-12B-v2-VL** (12B, OCRBench-v2 leader, 128K ctx)
- HF: `nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16` (also `-FP8`, `-NVFP4-QAD`)
- vLLM: `vllm serve nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-FP8 --trust-remote-code --quantization modelopt --video-pruning-rate 0`

**Deep/non-interactive reviewer: Nemotron-3-Super-120B-A12B** (120B total, 12B active MoE, 512 experts/22 active)
- Ollama: `ollama run nemotron-3-super`
- llama.cpp GGUF (Unsloth): `hf download unsloth/NVIDIA-Nemotron-3-Super-120B-A12B-GGUF --include "*UD-Q4_K_XL*"`; serve `llama-server -m ...UD-Q4_K_XL-00001-of-00003.gguf -ngl 99 -c 16384 -fa on --port 8001`
- HF NVFP4 for vLLM: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`
- **GB10 caveats:** throughput is contested — community llama.cpp/Ollama builds report ~14 t/s (memory-bandwidth-bound), while DGX Spark forum users report 65+ tok/s single-seq on the NVFP4 build with vLLM optimizations, though vLLM 26.03 hit two Blackwell kernel bugs (CUDA-graph illegal-instruction crash and CUTLASS grouped-GEMM/FlashInfer MoE FP4 failure) whose workarounds degrade the benchmark. The 66 GB GGUF needs ~73 GB at runtime — drop page cache (`sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'`) and stop Ollama before launching llama-server. **Ollama's MoE GGUF blobs are NOT compatible with upstream llama.cpp** (expert tensor layout differs: packed dim 1024 vs concatenated 4096) — use ggml-org/Unsloth GGUF. NVIDIA Spark deployment guide: github.com/NVIDIA-NeMo/Nemotron (usage-cookbook/Nemotron-3-Super/SparkDeploymentGuide).

**Multimodal omni option: Nemotron-3-Nano-Omni-30B-A3B-Reasoning** (text+image+audio+video, OCR, 256K ctx)
- HF: `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16` (also `-FP8`, `-NVFP4`); GGUF `unsloth/NVIDIA-Nemotron-3-Nano-Omni-30B-A3B-Reasoning-GGUF` (~25 GB at 4-bit; needs `mmproj-BF16.gguf` for vision; use llama.cpp not Ollama for vision). vLLM 0.20.0 required for serving the HF weights.

**Smallest fallback: Nemotron-3-Nano-4B** (~3 GB at 4-bit) for ultra-fast tool-routing.

### 3.5 NemoClaw + OpenShell stack
- **NemoClaw repo:** https://github.com/NVIDIA/NemoClaw (Apache-2.0). Reference stack to run OpenClaw/Hermes agents inside **OpenShell** sandbox (Landlock + seccomp + netns) with policy-governed inference. Early preview from March 16, 2026.
- **Docs:** https://docs.nvidia.com/nemoclaw/ (machine-readable index: https://docs.nvidia.com/nemoclaw/llms.txt)
- **Awesome list / presets:** https://github.com/VoltAgent/awesome-nemoclaw
- Inference profiles: NVIDIA cloud endpoint, `nim-local`, and `vllm`. Default-deny network policy in `nemoclaw-blueprint/policies/openclaw-sandbox.yaml`; presets for Slack/Jira/PyPI/Docker. **Telegram bridge** is a built-in auxiliary service. Local inference setup (per v0.0.60 release notes) supports NIM, Ollama, vLLM, DGX Spark, DGX Station.
- Onboard flow: install script → `nemoclaw onboard` (creates sandbox, configures inference, applies policy) → `nemoclaw <name> connect` → chat via OpenClaw TUI/CLI; messaging via Telegram bridge.

### 3.6 GB10 hardware facts (for the pitch)
Dell Pro Max with GB10: NVIDIA GB10 Grace Blackwell superchip (20-core Arm: 10× Cortex-X925 + 10× Cortex-A725 + Blackwell GPU, 6,144 CUDA cores), **128 GB LPDDR5X unified** memory on a 256-bit bus — Dell/NVIDIA quote **273 GB/s** (The Register, Oct 13 2025: "Nvidia is claiming 273 GB/s of memory bandwidth"; NVIDIA's Hot Chips 2025 disclosure cites a higher ~301 GB/s raw figure for the LPDDR5X-9400 fabric), **~1 PFLOP sparse FP4**, ConnectX-7 200 GbE (link two boxes → up to 405B-param models), DGX OS (Ubuntu 24.04 ARM), up to 4 TB SSD. ~$3,700–4,060. Real-world note (Jeff Geerling; Carmack): GPU power caps ~100 W; token gen on a 70B model ≈ 2.7 t/s (Apertus.ai measured Llama 3.1 70B) — **capacity, not speed, is the advantage.**

---

## 4. Competitive / funding / maturity scan (concise)

- **Incumbents (authoring + rules-driven validation):** **Hexagon** Intergraph Smart P&ID ("rules-driven design for validating against engineering practices, owners standards, safety practices"), **AVEVA** P&ID/Diagrams, **Bentley** OpenPlant, **Autodesk** AutoCAD Plant 3D, plus Octave's Facets P&ID (formerly Hexagon). These are CAD authoring tools with built-in rule checking on *native* smart-P&IDs — they do **not** solve *extraction from legacy scans/PDFs* well.
- **Extraction/validation specialists / startups:** **Pathnovo** (P&ID/isometric extraction, reconciliation against the instrument index, pre-certified connectors to SAP PM S/4HANA, IBM Maximo, AVEVA NET, Hexagon SmartPlant). Pathnovo's go-to-market is a free trial — "Send us 10 documents from your current project. We extract, reconcile, and show you exactly what we find in 48 hours… If the accuracy isn't what we promised, you owe us nothing" — with pricing "starts at Rs.75/page (approximately $0.90/page)." Others: Acuvate DiagramIQ, IPS iDrawings.
- **Market size:** Pathnovo's own marketing cites "a $58.7 billion industry as of 2026"; independent estimates diverge and are lower — Mordor Intelligence ~$48.8B (2025), Grand View Research ~$43.0B (2024)/$49.9B (2025), Research and Markets ~$54.4B (2026). Treat all as engineering-software-market proxies, not P&ID-specific.
- **Academic/agentic frontier:** TU Delft Process Intelligence Research (Schweidtmann group — pyDEXPI, ChatP&ID, rule-based autocorrection), TCS Research (Sakhinana multi-agent RAG), DLR (PID2Graph).
- **Maturity / accuracy reported:** Modular detection pipelines report ~90/90 precision/recall *with large proprietary training sets* (Azure sample / JCDE 2022); PID2Graph Relationformer ~82% node, ~77% connection on real OPEN100 sheets; rule-based graph autocorrection 100% on a *clean ground-truth graph*. **No fully-autonomous production deployment is publicly documented** — all credible workflows are human-in-the-loop (engineer reviews low-confidence extractions). ROI claims (~200% in manufacturing, per Pathnovo citing Capgemini) are vendor marketing.
- **Why unsolved:** (1) symbol detection is hard — tiny inter-class visual differences, noise, rotation, scanned artifacts; (2) line/connectivity extraction across crossings, page-breaks and dashed signal lines is brittle; (3) no large *public* labeled dataset with full-graph ground truth until PID2Graph (12 real sheets); (4) domain rules are project- and standard-specific; (5) errors are "cross-boundary" handoff issues; (6) high cost of being wrong on safety-critical drawings → mandatory human sign-off.

---

## 5. Full spec / build-plan for the GB10 + Nemotron + NemoClaw stack

### 5.1 System architecture

```
P&ID input (Telegram/Slack message: image, PDF, or DEXPI .xml / .graphml)
        │
        ▼
[Ingest]  ── DEXPI .xml ─→ pyDEXPI ─→ NetworkX graph
          ── .graphml ───→ nx.read_graphml ─→ NetworkX graph     ← FAST PATH (demo)
          ── image/PDF ──→ Nemotron-Nano-12B-VL (OCR+symbols) / YOLO detector ─→ graph builder
        │
        ▼
[Connectivity graph]  NetworkX: nodes=equipment/instruments/valves, edges=pipes/signals, attrs=tags
        │
        ▼
[Rule engine]  deterministic checks (§2.4) via VF2 subgraph isomorphism + tag-grammar/regex + graph reachability
        │            → structured punch-list (JSON: rule_id, severity, component, message, standard_ref)
        ▼
[Reviewer agent]  local Nemotron (Nano-30B interactive / Super-120B deep) narrates punch-list,
                  prioritizes by severity, explains each finding citing the standard
        │
        ▼
[Output]  punch-list posted to Telegram/Slack via NemoClaw Telegram bridge
        │
        ▼
[Optional GraphRAG Q&A]  "Which vessels lack a relief path?" → ContextRAG/CypherRAG over the graph → Nemotron answer
```

Everything runs inside the **OpenShell sandbox** on the GB10 with default-deny egress (only Telegram + local inference endpoints allowed) — the privacy/audit story.

### 5.2 Recommended fastest path
Start from **PID2Graph `.graphml`** (zero detection work) → NetworkX → rule engine → Nemotron narration → Telegram. Add a **deliberately-broken** synthetic P&ID (inject a missing PSV + duplicate tag via pyDEXPI) so the demo shows the agent catching real, named defects. Only if time remains, wire the Nemotron-Nano-VL image path for a "drop a screenshot" wow moment.

### 5.3 Hour-by-hour (single day, ~10 hr)
- **Pre-day (on MacBook → 64 GB USB):** download PID2Graph.zip (9.3 GB), Dataset-P&ID, pyDEXPI repo, and Nemotron GGUFs (Nano-30B UD-Q4 ~24 GB; optionally Nano-12B-VL; Super-120B ~66 GB likely won't co-fit on a 64 GB stick). Pre-pull Ollama tags. *Prioritize Nano-30B + Nano-12B-VL + datasets on the USB.*
- **H0–0.5:** GB10 setup — copy from USB, `ollama serve`, pull/load `nemotron-3-nano`, verify token speed.
- **H0.5–1.5:** NemoClaw `onboard`; configure OpenShell policy to allow Telegram + local inference; confirm a round-trip "hello" Telegram → Nemotron → Telegram.
- **H1.5–3:** Graph loader — `nx.read_graphml` + pyDEXPI parser; normalize node/edge attributes (tag, type, fail-position, line-number).
- **H3–5.5:** Rule engine — implement Tier A checks 1–6 as Python functions + a couple of VF2 rule-graphs. Emit JSON punch-list.
- **H5.5–6.5:** Reviewer agent prompt — feed JSON + graph summary to Nemotron-Nano-30B; produce ranked, standard-cited natural-language punch-list.
- **H6.5–7.5:** Wire punch-list → Telegram; add `/review <file>` and Q&A command.
- **H7.5–8.5:** Build the broken-P&ID demo case; add Tier B checks 7–12 if time.
- **H8.5–9.5:** GraphRAG Q&A (optional) + Nano-VL image ingest (optional/stretch).
- **H9.5–10:** Rehearse demo, prepare fallbacks.

### 5.4 Maximizing the Dell/NVIDIA stack in the pitch
- **All-local, zero cloud tokens:** P&IDs are sensitive IP; running Nemotron entirely on the GB10 = data never leaves the box. Cite IEC 61511 / data-privacy mandates.
- **OpenShell sandbox + default-deny egress + audit log:** "a rogue agent can't exfiltrate your plant drawings" — the exact enterprise security narrative NemoClaw is built for.
- **128 GB unified memory:** load a 120B reasoning model *and* a 12B VLM simultaneously — impossible on a 24–48 GB GPU. This is the GB10's unique selling point (capacity over speed).
- **Always-on agent:** the agent lives in Telegram/Slack, reviewing every P&ID revision automatically as it's dropped — "continuous compliance," not a batch tool.

### 5.5 Demo script (judges)
1. Drop a real OPEN100 P&ID `.graphml` into Telegram → agent replies in seconds with a clean/short punch-list. ("It runs entirely on this Dell box — nothing left the room.")
2. Drop the **broken** P&ID → agent flags: *"🔴 V-101 has no relief path (API 521); 🔴 duplicate tag PT-101; 🟠 FV-203 missing fail position (ISA-5.1); 🟠 pump P-12 missing discharge check valve (backflow risk)."*
3. Ask in natural language: *"Which vessels are missing a level instrument?"* → GraphRAG answer.
4. (Stretch) Drop a P&ID **screenshot** → Nano-VL extracts tags → same review.
5. Close on business value: hours-of-manual-review → seconds; pre-HAZOP gate; on-prem/private; audit-logged.

### 5.6 Risk mitigations / fallbacks
- **Detection underperforms** → fall back to `.graphml`/DEXPI ground-truth graphs (the primary path anyway).
- **120B too slow / unstable** → use Nano-30B for all interactive turns; reserve Super-120B for an offline "deep review" button, or drop it entirely.
- **USB capacity (64 GB)** → carry Nano-30B + Nano-12B-VL + datasets; pull Super-120B via Ollama on-site only if network allows.
- **llama.cpp/Ollama GGUF incompatibility on GB10 (sm_121)** → use ggml-org/Unsloth GGUF, `-fa on`, drop page cache before load; do not reuse Ollama's MoE blob with upstream llama.cpp.
- **NemoClaw is early-preview (Mar 2026), may break** → fallback to plain Ollama + a minimal `python-telegram-bot` script; keep OpenShell as the "security story" even if you demo via the simpler bridge.
- **Rule false positives** → keep rules deterministic and conservative; mark severity; always frame as "human-in-the-loop punch-list," not auto-approval (matches industry reality).

---

## Recommendations
1. **Commit to the graph-first path now.** Build loader → rule engine → Nemotron narrator → Telegram in that order; treat detection/VLM as stretch. Decision thresholds: if Nano-30B answers in <5 s and the rule engine runs on a real OPEN100 graph by H5.5, add Tier B + GraphRAG; if behind schedule, ship Tier A only.
2. **Pre-stage everything on the USB from the MacBook** before arriving — model downloads are the #1 day-of time sink. If Super-120B won't fit, drop it; Nano-30B is the workhorse.
3. **Lead the pitch with business + security**, demo the broken-P&ID catch, and explicitly name the standards (ISA-5.1, API 521, IEC 61511) — judges reward concrete enterprise grounding.
4. **Keep a deterministic core.** The rule engine (not the LLM) produces findings; the LLM only explains. This is the credibility differentiator and the fallback if inference is slow.

## Caveats
- NemoClaw/OpenShell are early-preview (from March 16, 2026) and explicitly "not production-ready"; APIs may change. The fan/marketing sites (nemoclawai.io, nemoclaw.run) contain testimonials — treat as non-authoritative; rely on github.com/NVIDIA/NemoClaw and docs.nvidia.com/nemoclaw.
- GB10 token-generation speed is genuinely limited (~2.7 t/s on 70B; 120B MoE throughput is disputed between ~14 t/s and 65+ t/s depending on runtime/quant and unresolved Blackwell kernel bugs) — plan interactivity around Nano-class models and benchmark on-site before committing the Super-120B to a live demo.
- Memory-bandwidth figures vary by source (Dell/NVIDIA marketing 273 GB/s vs Hot Chips ~301 GB/s raw) — quote 273 GB/s, the official spec.
- ROI/market figures ($58.7B market, 200% ROI) are vendor/marketing claims; independent market estimates are lower (~$43–54B) and not P&ID-specific.
- The "rule-based autocorrection 100% accuracy" is on a clean ground-truth graph, not on noisy extracted graphs — real-world accuracy depends entirely on upstream digitization quality.
- arXiv 2603.22528 (ChatP&ID) and 2604.16513 (SynthPID) carry 2026 IDs; verify final venue/version. The published PID2Graph real-world subset is only **12 sheets** (OPEN100, 57–210 components and 28–118 edges each); the 60 real-world sheets mentioned in the companion paper are private training data, not in the Zenodo download.
- ISA-5.1 full standard is paywalled; public letter-code tables are summaries — verify against the official 2024 edition before any production use.
