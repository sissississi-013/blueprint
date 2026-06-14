# Project — P&ID Reviewer: A Local GB10 Engineering-Diagram Validation Agent

> **This is the build for the day.** See [`hackathon-context.md`](./hackathon-context.md) for event rules and [`sponsor-tech-and-advantages.md`](./sponsor-tech-and-advantages.md) for the hardware/stack/leverage analysis. This file is the project spec + build playbook.

---

## TL;DR

Build the **P&ID engineering-diagram validation agent**. It has strong corporate defensibility, a clean local-first data story, and a genuine unfilled gap: 2024–2026 research has solved P&ID digitization and Q&A, but **rule-based compliance/validation agents** (ISA-5.1 tag checks, missing relief valves/interlocks) exist only as "future work." The one published quantitative attempt at LLM HAZOP safety reasoning found "the proportion of semantically valid scenarios remained low (0.19 to 0.37)" — a wide-open, demoable opportunity.

**The single-day demo that wins:** clone an existing symbol-detector + the open PID2Graph / Dataset-P&ID data, extract a connectivity graph, then run a local **Nemotron** model as a "P&ID reviewer" that checks ISA-5.1 tag formats, finds orphaned line numbers, and flags missing safety instrumentation — all on the GB10, sandboxed by OpenShell.

---

## The Product

**"P&ID Reviewer"** — an always-on **local** agent that ingests a P&ID and returns a **compliance punch-list**, each finding tied to the standard it violates.

### Why this wins the rubric
- **Corporate/regulated use case** (offshore/process engineering, asset integrity) — exactly what judges favor.
- **Local-first is the whole point**: confidential engineering drawings never leave the box. Air-gapped, auditable, sandboxed.
- **Real, unfilled gap**: digitization + Q&A are solved; *automated compliance validation* is not.
- **Demoable ROI**: "Finding a numbering error at IFC costs hours; finding it during construction costs days and material write-offs."

---

## Required Stack (non-negotiable)

> **OpenClaw + NVIDIA NemoClaw + OpenShell**, with **NVIDIA Nemotron 3** models, all running **locally on the GB10**.

| Layer | Component | Our usage |
|---|---|---|
| Agent framework | **OpenClaw** | Always-on gateway; our reviewer checks are OpenClaw **skills**; output channel (Telegram/Slack). |
| Reference distribution | **NVIDIA NemoClaw** | One-command install of the stack; serves **Nemotron 3** via Ollama; provides Cursor/Claude Code skills. |
| Secure runtime | **OpenShell** | Sandboxes execution — deny-by-default network + filesystem isolation, live policy approval. **Demo this as a feature.** |
| Models | **Nemotron 3** (Nano / Super 120B / Omni / V2 VL) | Local inference only — **no cloud LLM calls** (scored). |

If any layer is missing, the submission fails the stack requirement *and* loses the local-first scoring bucket.

---

## Judging Rubric — How We Win (official weights)

| Criterion | Weight | Our play |
|---|---|---|
| **Local-first + always-on** | **30%** | 100% on-GB10 inference (Nemotron via Ollama), **zero cloud calls**. Make it **proactive**: the reviewer watches a drawings folder/inbox and auto-emits a punch-list when a new P&ID lands — "acts on its own over time," not request-response. Show OpenShell's deny-by-default network blocking egress live. |
| **Business value** | **30%** | Lead with a **quantified** corporate pain: offshore asset integrity, "150-day anomaly→resolution cycles," incomplete as-builts, error-cost escalation IFC→construction. Position against Pathnovo's monetized ISA-5.1 cross-validation (99.5% / 600 P&IDs). |
| **Demo + pitch** | **30%** | Budget real time to rehearse a tight **5-minute pitch**. Open with the gap (HAZOP paper: 0.19–0.37 valid scenarios), show punch-list on a real sheet, end on "data never leaves the box." Pre-compute headline findings so it never stalls. |
| **Technical execution** | **10%** | Only 10% — get it working end-to-end and **don't break on stage**; use the stack correctly. Don't over-engineer at the expense of the three 30% buckets. |

**Strategic takeaways (from the weights):**
- **90% of the score is narrative + local-first + working demo**; only 10% is raw engineering. Resist gold-plating the detector — the `.graphml` fast-path exists precisely to protect this balance.
- **"Acts on its own over time" is explicit** → ship the proactive/scheduled trigger, not just a chatbot.
- **Any cloud API call directly costs the biggest bucket.** Keep everything on the GB10.
- **Small-team scoring bonus** stacks on top — keep the team tight (2–3) and scope sharp.

---

## Why Validation, Not Drafting

Day-to-day P&ID pain is **review and compliance**, not drawing. A P&ID review checklist (iFluids) covers:
- Line numbering and class breaks
- Instrument tag verification per **ISA-5.1**
- Control loop completeness
- Relief system paths per **API 521**
- SIS boundary definition per **IEC 61511**
- Equipment nozzle consistency

Most common errors: **missing spec breaks at pressure-class transitions, incorrect control valve fail positions, duplicate instrument tags.**

### ISA-5.1 tags are a checkable grammar
Tags follow **First Letter + Modifier (optional) + Sequence/Loop Number**:
- First letter = measured variable (P, F, T, L…)
- Subsequent letters = function (I, R, C, T, A…)

This is exactly what an LLM agent can validate against an extracted tag list. Vendor **Pathnovo** reports **"99.5% measured accuracy on ISA-5.1 tag identification across 600 P&IDs / 10,247 tags,"** cross-validating extracted tags against the instrument index — proof the workflow is real and valued.

### Asset-integrity urgency (the ROI framing)
- Independent operators report **"150-day cycles between anomaly detection and resolution"** from disconnected data sources and manual inspection (Vidya case study).
- **API RP 2SIM** management depends on design drawings, as-built records, and inspection history — but per AsInt, *"older platforms often don't have full as-built drawings or complete inspection records. You end up spending weeks just gathering information."*

This is a document-intelligence + consistency-checking problem the agent attacks directly: **"we don't have complete as-builts; find what's missing/inconsistent."**

---

## Architecture — Detector → Graph → LLM Reasoner

**Critical design rule:** Do **NOT** ask a VLM to "read the whole P&ID." The literature is consistent that VLMs are weak at raw diagram reasoning:
- *"Do Vision-Language Models Really Understand Visual Language?"* (arXiv 2410.00193): LVLMs "have a limited capability for genuine diagram understanding" and lean on background-knowledge shortcuts.
- On **FlowLearn**, GPT-4V/Claude-3 score only F1 = 0.22/0.30 translating flowcharts to Mermaid.

**Instead:** use a trained detector for symbols/text → build the graph **deterministically** → let the LLM reason over the **structured graph**. This is the ChatP&ID / Talking-like-P&IDs design, and it's why graph-based input "improves accuracy by 18% over raw image inputs."

### Pipeline (all local on GB10, orchestrated by OpenClaw, sandboxed by OpenShell)

1. **Ingest** a P&ID image (from open datasets, or a scanned sample).
   - Pre-load symbols/lines via a cloned detector (YOLOv5/Detectron2 on Dataset-P&ID's 32 classes), **OR**
   - **To save the day:** start directly from **PID2Graph's `.graphml` ground-truth graphs** — skip training entirely, spend the day on the agent.
2. **Build the connectivity graph** in **NetworkX** (nodes = equipment/instruments with tags + bbox; edges = lines). Render the graph for the "wow."
3. **Reason with a local Nemotron** as a reviewer agent running concrete checks:
   - **ISA-5.1 tag validity** — first-letter/function grammar; duplicate tags; malformed loop numbers.
   - **Line-number / tag consistency** — orphan lines; tags on the drawing not in the instrument index and vice-versa (the exact cross-validation Pathnovo monetizes).
   - **Missing safety instrumentation** — e.g., a pressure vessel with no relief path; a control loop with no fail-position annotation (the open gap the HAZOP paper shows LLMs *almost* do).
4. **Return a punch-list** over Telegram/Slack (NemoClaw's native channel), each finding tied to the standard it violates.
5. **(Optional)** Natural-language Q&A mode over the graph (ChatP&ID-style GraphRAG).

---

## Models (fits the box)

| Model | Size | Role |
|---|---|---|
| Nemotron 3 Nano | 31.6B total / ~3B active (hybrid Mamba-Transformer MoE, ~24 GB; 4B variant ~5 GB) | Fast lane; interactive turns; rule reasoning |
| Nemotron 3 Super 120B-A12B | 120B total / 12B active (NemoClaw default) | Deep rule reasoning (use sparingly: **30–90 s/response** on GB10) |
| Nemotron 3 Nano Omni 30B-A3B | ~25 GB at 4-bit, 256K context, OCR/GUI/vision/audio | Multimodal read of legend/notes |
| Nemotron Nano V2 VL | 12B | Multimodal; "leading accuracy on OCRBench v2" |

All open-weight, up to 1M-token context, run via vLLM/SGLang/Ollama/llama.cpp with day-zero GGUF support.

**USB drive planning:** pre-pull one Nano-class model (fits a 64 GB drive with room to spare) + optionally a **quantized 120B GGUF** (full BF16 won't fit a 64 GB drive — pull quantized or download on the box). A multimodal Nano (Omni / V2 VL) is the workhorse for reading diagrams.

---

## Build Playbook — Staged for One Day

| Hours | Goal |
|---|---|
| **0–1** | Stand up **NemoClaw** on the GB10 per NVIDIA's tutorial (Ollama + Nemotron, OpenShell sandbox, Telegram). Pre-pull a Nano-class model from USB; queue the 120B GGUF. |
| **1–3** | Load **PID2Graph / Dataset-P&ID**; build the **NetworkX** graph + a renderer. |
| **3–6** | Write the reviewer agent's checks (ISA-5.1 grammar, tag/line cross-validation, missing-relief-path heuristic) as **OpenClaw skills**. |
| **6–8** | Wire the punch-list output to Telegram/Slack; add GraphRAG Q&A; rehearse the demo on 2–3 sheets. |

### Decision thresholds (de-risk early)
- **Team has a CV/ML engineer** comfortable cloning a detector → go full Thread 1 (train/clone detector).
- **Team is purely LLM/prompt-focused** → still do Thread 1, but **start from PID2Graph `.graphml`** to bypass vision entirely.
- **Detector scores poorly** (edge/connection mAP well under the ~75% PID2Graph baseline) on sample sheets within the first 2 hours → **abandon training, switch to `.graphml` ground-truth path.** Don't sink the day into detection.
- **Nemotron-30B can't reliably apply ISA-5.1 rules** in first prompt tests → escalate to the **120B for the reasoning step only**.

### Live-demo de-risking
- The 120B is **30–90 s/response** → **pre-compute headline findings**; use Nano-30B for anything interactive.
- Have a **fallback sheet** whose graph you've already validated.
- Everything is local + sandboxed → immune to flaky venue Wi-Fi / cloud rate limits.

---

## Resources to Clone (mostly open)

### Datasets
- **Dataset-P&ID** (Paliwal et al., Digitize-PID, arXiv 2109.03794) — 500 synthetic P&IDs, 32 symbol classes, symbol/line/text annotations. YOLO repackage on HuggingFace: `hamzas/digitize-pid-yolo`.
- **PID2Graph** (arXiv 2411.13929, IEEE DSAA 2025) — first public **real-world** P&ID dataset with full graph labels; ground truth as `.graphml`, imports straight into NetworkX. **Zenodo record 14803338.** Relationformer reports symbols 73.49% / nodes 82.18% / connections 76.79%; edge detection beats modular approach by >25%.
- ⚠️ **Don't conflate** the Paliwal synthetic "Dataset-P&ID" with the separate ASU Zenodo "PID_dataset" of scraped industrial drawings.

### Reference architectures
- **Microsoft `Azure-Samples/digitization-of-piping-and-instrument-diagrams`** — full reference (symbol → text → line → graph), detects ~80% of assets/connections. Companion Korean study (Kim et al. 2022, JCDE) hit >90/90 precision/recall on 75K-symbol training.

### Cloneable detector repos
- `ch-hristov/p-id-symbols` (YOLOv5 + Kaggle `hristohristov21/pid-symbols`)
- `mohdahmad242/PID-detection` (Detectron2)
- `aneeshbhattacharya/Automated-PnID-Symbol-Detection-and-Labelling` (PyTorch + EAST + MMOCR)
- `heyad/Eng_Diagrams` (2,432 engineering-symbol instances)
- `mgupta70/PID_Symbol_Detection`
- ⚠️ GitHub star counts were not verifiable from search — confirm activity/issues before relying on any single repo.

### The agentic frontier (our differentiator's neighbors)
- **ChatP&ID** ("GraphRAG for Engineering Diagrams," arXiv 2603.22528, TU Delft, 2026) — agentic GraphRAG over P&IDs; graph reps "+18% accuracy over raw image," "−85% token cost vs smart-P&ID files," "+40% with VectorRAG + PathRAG."
- **"Talking like P&IDs"** (arXiv 2502.18928, 2025) — DEXPI → Neo4j LPG via `pyDEXPI`, graph-RAG.
- **Sakhinana et al. (TCS)** — hierarchical multi-agent RAG for P&ID QA (arXiv 2409.00082) and regulation-compliant schematic generation (arXiv 2412.05937).
- Agentic P&ID generation (arXiv 2412.12898).

### The proven gap (cite this in the pitch)
- **Lee, Park, Oh & Ma, "Can large language models automate the HAZOP process without human intervention?", Safety Science (2026)** — tested GPT-4o / 4o-mini / LLaMA / Gemini generating HAZOP worksheets from a single P&ID. Textual similarity high (F1 > 86%), but **"the proportion of semantically valid scenarios remained low (0.19 to 0.37)," safeguards heavily biased toward procedural measures.** Conclusion: LLMs are supportive tools, not replacements for expert-led HAZOP — concrete, citable evidence of the open gap.

---

## Recommendation Summary

- **Commit to Thread 1 as the core build.** Keep any "Thread 2" idea as a 30-minute sizzle only if time remains.
- The novel work is **prompt/agent logic over a structured graph** (hours, not weeks). Detection + graph data are pre-built and open.
- Frame the pitch around **offshore asset integrity**: incomplete as-builts, expensive late-stage error discovery, regulated data that can't leave the premises.

---

## Caveats & Risks

- **Recency/peer-review:** ChatP&ID (2603.22528), One-Sentence-One-Drama (2605.22144), SynthPID (2604.16513) are **2026 preprints, not peer-reviewed**; self-reported numbers are on their own tasks. **PID2Graph (DSAA 2025)** and **Lee et al. (Safety Science 2026)** are peer-reviewed.
- **VLM limitation is real:** treat any "VLM reads the whole P&ID" approach as high-risk. Structured-graph reasoning beats raw-image reasoning for diagrams.
- **Security:** NVIDIA warns "no sandbox offers complete protection against advanced prompt injection," and OpenClaw's broad permissions are a documented risk. Fine for a hackathon — and **mention OpenShell sandboxing as a feature** in the pitch.
- **Cloud APIs:** allowed but discouraged. The entire value proposition (offshore/regulated data, on-prem mandate) **collapses if you call a cloud API** — keep everything on the GB10.
