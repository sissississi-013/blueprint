# Sponsor Technologies & Unfair Advantages

> Research reference for the Dell × NVIDIA Hackathon. Covers the hardware and the required stack (OpenClaw + NVIDIA NemoClaw + OpenShell + Nemotron), plus the leverage points a team can exploit. See `hackathon-context.md` for event rules.

---

## 1. The Hardware — Dell Pro Max with GB10

A compact deskside "AI supercomputer" (model FCM1253), internally near-identical to NVIDIA's DGX Spark. Built on the **NVIDIA GB10 Grace Blackwell Superchip**.

| Spec | Detail |
|---|---|
| CPU | 20-core Arm Grace (10× Cortex-X925 + 10× Cortex-A725) |
| GPU | Blackwell, 6,144 CUDA cores, **up to 1 petaflop (1000 TFLOPS) sparse FP4** |
| Memory | **128 GB LPDDR5X unified** (shared CPU+GPU), 273 GB/s, 256-bit bus |
| Storage | Up to 4 TB NVMe (PCIe Gen4) |
| OS | NVIDIA DGX OS 7 (Ubuntu-based) — ships with CUDA, drivers, PyTorch/TensorFlow; compatible with **Docker, vLLM, NVIDIA NIM** |
| Networking | Dual 200GbE **ConnectX-7** Smart NICs (QSFP), 10GbE RJ-45, Wi-Fi 7, BT 5.4 |
| Clustering | Tether two units via ConnectX-7 → run models **up to ~400B params** |
| Single node | Supports models **>200B params** locally |
| Power / size | 280W USB-C adapter, ~150×150×51 mm, ~2.9 lb |
| Price (context) | ~$3,999 MSRP base; ~$5,780 as-tested |

**Why it matters:** 128 GB of unified memory is the headline. It lets you run frontier-class open models — and feed them very long contexts — entirely on-device, with no cloud and no per-token cost.

---

## 2. NVIDIA Nemotron (the models)

The open model family that runs locally on the box. Current generation is **Nemotron 3: Nano, Super, Ultra**.

- **Fully open**: weights, training datasets, and recipes published on Hugging Face for commercial use. Also available as **NVIDIA NIM** microservices.
- **Architecture**: hybrid **Mamba-Transformer Mixture-of-Experts (MoE)** — high throughput with strong accuracy.
  - **Nano**: ~3.2B active / ~31.6B total. Fits fully in GB10 memory; fast time-to-first-token. Great for sub-agents and the "fast lane."
  - **Super**: ~120B total / ~12B active. The default NemoClaw model (`nvidia/nemotron-3-super-120b-a12b`). High-accuracy reasoning + tool calling for multi-agent systems.
  - **Ultra**: largest, best reasoning for mission-critical workloads.
- **Efficiency tricks**: native **NVFP4** 4-bit training (Super/Ultra) → small footprint on Blackwell; **LatentMoE**; **Multi-Token Prediction (MTP)** for native speculative decoding (faster generation).
- **Context**: up to **1M tokens** — whole codebases, long histories, big RAG payloads without chunking.
- **Reasoning budget control**: tune latency vs. reasoning depth at inference time.
- **Strengths**: agentic tool use, coding, math, RAG, multimodal vision, speech, safety.

---

## 3. OpenClaw (the agent framework)

- Open-source (**MIT**), self-hosted, **always-on** agent runtime. Began Nov 2025 as "Clawdbot"; became the fastest-growing OSS repo in GitHub history.
- **Gateway daemon** (long-lived Node.js process) is the control plane: sessions, routing, auth, tool execution. Runs 24/7 in the background (e.g., as a systemd service).
- **Connects LLMs to real systems**: local filesystem, messaging channels (WhatsApp, Slack, Telegram, Discord), a real browser, and the shell/CLI.
- **Takes actions, runs on a schedule, and persists memory** — not just request/response chat.
- **Skills** are the extension mechanism (markdown + TypeScript plugins), distributed via Clawhub; high-risk skills can require explicit confirmation.
- **Multi-agent**: define multiple agents, each with its own model/workspace, switchable via `/agent`.
- Config lives in `~/.openclaw/openclaw.json`; `openclaw onboard` wizard; gateway default port 18789. Model-agnostic (Anthropic, OpenAI, Gemini, Ollama, local models).

---

## 4. NVIDIA NemoClaw (the reference stack)

Announced **March 16, 2026**. NVIDIA's opinionated, enterprise-grade distribution that installs **OpenClaw + Nemotron + OpenShell in a single command** — "OpenClaw with guardrails."

- Install: `curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash`, then `nemoclaw onboard`.
- **Two components**: a thin TypeScript **plugin** (registers an inference provider + the `/nemoclaw` slash command, runs in-process with the OpenClaw gateway) and a versioned Python **blueprint** that orchestrates OpenShell resources (resolve → verify digest → plan → apply).
- Handles onboarding, lifecycle, blueprint versioning, sandbox setup, and inference routing.
- **Ships agent skills for Cursor and Claude Code** — your coding assistant can guide setup, inference, policy, monitoring, deployment, security, and troubleshooting.
- Default inference target is `nvidia/nemotron-3-super-120b-a12b`; **local inference via Ollama / vLLM** is supported (key for the local-first requirement).

---

## 5. OpenShell (the secure runtime)

Part of the **NVIDIA Agent Toolkit** — a general-purpose, governance-first agent sandbox. This is the "no host filesystem or network exposure" layer.

- **Topology**: host Docker daemon → **gateway container** (credential store + L7 proxy + embedded **k3s** control plane) → **sandbox runs as a Kubernetes pod**.
- **Out-of-process policy enforcement**: the policy layer sits *outside* the agent process, so the agent cannot override its own controls via prompt tricks.
- **Filesystem**: confined to `/sandbox` and `/tmp` (read-write); system paths read-only.
- **Network**: deny-by-default egress. Blocked actions surface in a **TUI for operator approval** — no silent failures; live policy updates without restart.
- **Inference routing**: the agent only talks to `inference.local`. OpenShell intercepts every call and forwards it to the configured provider; the **L7 proxy injects credentials at egress**, so secrets never enter the sandbox. Routes to NVIDIA Endpoints, OpenAI, Anthropic, Gemini, **local Ollama, local vLLM/TensorRT-LLM/llama.cpp**, or a host-side **Model Router** (port 4000) that picks from a model pool per policy.
- **Agent-aware policy** evaluated at binary / destination / method / path level; new skills are verified under the same controls.

---

## 6. Unfair Advantages To Leverage

These are the leverage points that distinguish a winning build from a generic cloud chatbot. The whole event is engineered to reward **local-first** — lean into it hard.

### A. Run a frontier-class model *fully local* (the 128 GB advantage)
- Run **Nemotron Super (120B)** or large quantized models entirely on the box. Most teams (and most cloud-throttled hackathon projects) can't show a 100B+ model running with zero network. Make that visible in the demo.
- Exploit the **1M-token context**: ingest an entire company knowledge base / codebase / contract set directly, minimizing RAG plumbing — or supercharge RAG with huge retrieval windows.

### B. "Your data never leaves the box" is the winning business narrative
- The judging favors **business/corporate** use cases, and the differentiator the sponsors are selling is local + private. Build for **regulated, data-sensitive verticals**: healthcare, legal, finance, defense, M&A diligence, HR/PII, on-prem enterprise IT.
- The pitch writes itself: *zero data egress, full audit trail, runs air-gapped.* OpenShell's sandbox + deny-by-default networking is your compliance story — and it's already built.

### C. Turn OpenShell guardrails into a *feature*, not friction
- Demo the **live policy-block TUI**: show the agent attempting an unauthorized action and being stopped by out-of-process enforcement. Judges and enterprise buyers love *visible* governance.
- Frame it as "an autonomous agent with real corporate tool access that *physically cannot* exfiltrate data or run unreviewed code."

### D. Build *always-on / proactive*, not request-response
- OpenClaw is purpose-built for persistent agents that run on a schedule and have memory. A deskside box that runs 24/7 is the perfect host. Build something that **monitors, triggers, and acts on its own** (watches an inbox/queue, reconciles data nightly, escalates anomalies) rather than a chatbot you have to poke. This is far more memorable in a demo.

### E. Tiered multi-model routing (Nano + Super) for speed *and* smarts
- Use the **Model Router**: route easy/interactive turns to **Nemotron Nano** (fast, fits in memory, low latency) and hard reasoning to **Super/Ultra**. This is literally Dell's own reference scenario — it gives you a snappy demo *and* deep reasoning when needed.
- Combine with **reasoning-budget control + MTP speculative decoding + NVFP4** to keep latency tight on stage.

### F. Free, unmetered compute = do expensive things others won't
- No per-token cost means you can **fine-tune / LoRA Nemotron on domain data**, pre-compute large embedding indexes, batch-process big document sets, or run long agent loops — all offline. DGX OS ships the tooling (CUDA, PyTorch, vLLM, NIM). Use it to show depth competitors can't afford in the cloud.

### G. Operational edge: come prepared, beat the day-of internet
- Organizers said the boxes are bare beyond login and **day-of internet will be slow** — bring everything on a **flash drive**: model weights (Nemotron checkpoints), datasets, your repo, Python/node deps, Docker images, and a tested `nemoclaw onboard` config. Teams that arrive and start `curl`-ing downloads will lose hours.
- Pre-write and rehearse the install path (`nemoclaw.sh` → `onboard` → local Ollama/vLLM provider) so setup is minutes, not the morning.

### H. Use the agent to build the agent
- NemoClaw **ships skills for Cursor and Claude Code**. Wire those in so your coding assistant already knows the stack's setup, policy, and monitoring conventions — faster iteration than reading docs live.

### I. Demo reliability
- Because the final demo *must* run on the box and everything is local + sandboxed, you're immune to flaky venue Wi-Fi and cloud rate limits mid-pitch. Engineer for a fully offline demo and you remove the most common live-demo failure mode.

### J. Team-size scoring bonus (strategy, not tech)
- Smaller teams get rubric bonus points. A tight, senior **team of 2–3** that ships cleanly can out-score a larger team — keep scope sharp and the build crisp.

---

## 7. Where This Points (candidate directions)

High-leverage builds that stack multiple advantages above:

- **On-prem compliance/diligence agent** — ingests confidential docs (contracts, financials, PII) with 1M-token context, answers + drafts, never egresses. (A + B + C)
- **Always-on IT/ops co-pilot** — watches logs/tickets/alerts 24/7, triages and proposes fixes inside the sandbox, escalates with an audit trail. (C + D)
- **Local financial/healthcare analyst** — fine-tuned Nemotron on domain data, heavy local batch processing, air-gapped. (B + F)
- **Tiered enterprise assistant** — Nano front-end for instant answers, Super for deep reasoning/tool use, all routed locally. (A + E)

> Common thread: pick a use case where *local + private + always-on* is the reason it's valuable — not an incidental detail. That alignment with the sponsors' thesis is itself an unfair advantage.
