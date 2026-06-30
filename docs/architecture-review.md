# Architecture Review — kas (Kasra's Agentic Shell)

**Status:** Draft · **Date:** 2025-07-11 · **Owner:** Kasra · **Type:** architecture-review
**Run:** kas-arch-review · **Snapshot:** 2025-07-11 · **Components:** kas (client), kas-server, MLX/Llama.cpp backends
**Grounding:** `agent/`, `server/`, `pyproject.toml`, `Makefile`

> Framework: `frameworks/architecture-review.md` · grounds-in ATAM, Well-Architected, ISO 25010.

## 1. Subject & scope
**Subject:** Kasra's Agentic Shell (KAS) — a local-first, offline-first agentic development environment that runs frontier open models on Apple Silicon (MLX) or NVIDIA (llama.cpp/GGUF) behind an Anthropic Messages API-compatible server, driven by an agentic TUI.

**Scope:** The full system: `kas` CLI/TUI client (`agent/cli.py`, `agent/tui/`), the inference server (`server/`), pluggable backends (`server/backends/mlx.py`, `server/backends/llama_cpp.py`), the agentic loop (`agent/core/loop.py`), tool system (`agent/adapters/tools/executor.py`), context compaction (`agent/core/compaction.py`), KV-cache persistence (`server/core/kvpersist.py`), and the model registry (`server/registry.py`).

**C4 Level:** System context + container (client, server, GPU backend) + component (loop, compaction, registry, tools).

**Goals:**
- **Offline-first:** Nothing leaves the machine; all inference local.
- **Cross-platform:** Apple Silicon (MLX) and NVIDIA/CPU (llama.cpp/GGUF).
- **Anthropic API-compatible:** Drop-in replacement for the Anthropic SDK.
- **Agentic:** Tool use, streaming, thinking, subagents, KV-cache continuation, local recall, surgical edits.

## 2. Quality-attribute drivers (scenarios)
| Driver | Scenario (source→stimulus→artifact→response→measure) | Priority |
|--------|------------------------------------------------------|----------|
| **Security (offline-first)** | Client sends messages to local server → local server → GPU backend. Response: no network egress; all weights cached locally. Measure: 0 telemetry calls; all traffic on 127.0.0.1:8765 (`server/cli.py:_port_in_use`, `agent/cli.py:_is_local_url`). | High |
| **Performance (GPU serialization)** | Multiple resident models submit GPU work → Metal command buffers → GPU watchdog timeout (uncatchable C++ abort). Response: process-wide `GPU_LOCK` serializes all GPU work (`server/backends/_gpu.py`). Measure: no GPU watchdog kills; requests queue rather than overlap. | High |
| **Performance (decode speed)** | Long sessions decode slower (full-attention layers) → decode rate drops → compaction triggers. Response: `agent/core/compaction.py:classify_compaction` fires "soft" (decode rate < frac of baseline) or "hard" (exceeds 85% context window). Measure: decode rate recovers post-compaction. | High |
| **Reliability (model loading)** | Client calls `kas serve` → server downloads/loads multi-GB model → port preflight blocks if already in use (`server/cli.py:_port_in_use`, `Makefile:start`). Response: fails loud and early, never silently binds to wrong process. Measure: 0 dead servers holding GPU/port. | High |
| **Reliability (server lifecycle)** | `kas` CLI spawns `kas-server` as detached subprocess (`agent/cli.py:_spawn_server`) → waits for readiness via `/v1/models` polls (`_wait_for_server`). Response: shows live download progress; gives up after stall. Measure: reliable server start/stop. | Medium |
| **Modifiability (pluggable backends)** | Add a new backend (e.g., CUDA/ROCm) → implement `EngineLike` protocol (`server/core/ports.py`) → register via `make_engine` (`server/backends/__init__.py`). Response: no changes to routing or HTTP adapters. Measure: new backend drops in. | Medium |
| **Modifiability (tool plugins)** | Add a new tool → create a mixin (e.g., `_bash_tools.py`) → add method `tool_<name>` → `ToolRunner` dispatches via MRO (`agent/adapters/tools/executor.py:run`). Response: no changes to dispatch logic. Measure: new tool works without touching core. | Medium |
| **Operational (context persistence)** | Server restarts → KV cache delta files on disk (`server/core/kvpersist.py`) → warm resume by replaying deltas. Response: no cold re-prefill; context restored. Measure: resume time ≈ delta replay, not full load. | Medium |
| **Usability (TUI)** | User types task → TUI streams thinking/text/tool_use via SSE (`server/adapters/http/sse.py`) → renders in three panels (`agent/tui/app.py:AgentApp`). Response: live streaming, command palette, theme switching. Measure: responsive, non-blocking. | Medium |
| **Correctness (continuation caching)** | Next turn's prompt shares prefix with previous → server reuses KV cache via `try_continuation` (`server/core/continuation.py`). Response: fast append-only cache hit, not full re-prefill. Measure: `cached_tokens` > 0 on continuation. | Medium |

## 3. Pillar scorecard
| Pillar | Score | Evidence | Risk / sensitivity |
|--------|-------|----------|--------------------|
| **Reliability** | 🟢 | Port preflight (`server/cli.py`), GPU serialization (`server/backends/_gpu.py`), model registry with LRU eviction (`server/registry.py`), health polling (`agent/cli.py:_wait_for_server`), error handling in routes (`server/app.py:validation_handler`, `fallback_handler`). | GPU watchdog kill is the single biggest risk — mitigated by `GPU_LOCK`. |
| **Performance efficiency** | 🟢 | KV-cache continuation (`server/core/continuation.py`), on-disk KV persistence (`server/core/kvpersist.py`), context compaction (`agent/core/compaction.py`), GPU memory budget (`server/registry.py:_evict_to_make_room`), SSE streaming (`server/adapters/http/sse.py`). | Long prefill without pings can trip client read timeouts — mitigated by `KEEPALIVE_SECS` in `server/core/pipeline.py`. |
| **Security** | 🟢 | Local-only server (127.0.0.1 default, `server/cli.py`), no telemetry (README), model weights cached locally (HuggingFace Hub), body size limit (`server/app.py:MAX_BODY_BYTES`), sandboxed file tools (`agent/adapters/tools/files.py:PathResolver`). | Sandbox only confines file tools, NOT bash (`agent/adapters/tools/executor.py` notes this). |
| **Cost / efficiency** | 🟢 | Quantized models (4-bit default), KV cache quantization (8-bit, `server/backends/mlx.py:KV_BITS`), GPU memory budgeting (`server/registry.py:_budget_gb`), model eviction LRU. | Multi-model co-residency can exceed GPU memory — explicitly budgeted and evicted. |
| **Operational excellence** | 🟢 | `Makefile` targets (`start`, `stop`, `serve`, `doctor`), server lifecycle management (`agent/cli.py:_spawn_server`, `_wait_for_server`), logs (`server.log`), PID file (`server.pid`), `kas doctor` for health checks. | Daemon mode requires `lsof` preflight; stale processes can hold ports. |
| **Modifiability / evolvability** | 🟢 | Hexagonal architecture (`agent/cli.py` composition root, `agent/ports/` protocols, `agent/adapters/` concrete implementations), backend factory (`server/backends/__init__.py`), tool mixins (`agent/adapters/tools/executor.py:MRO`), pluggable embeddings (`agent/adapters/embeddings/`). | Legacy `agent/main.py` is a 1600-line back-compat facade (docstring); new code should import from specific modules. |

## 4. Trade-off & sensitivity points
| Decision | Attribute bought | At the cost of | Bake-in risk |
|----------|------------------|----------------|--------------|
| **GPU serialization (single `GPU_LOCK`)** | Correctness: no GPU watchdog kills. | Concurrency: requests queue, not overlap. | Throughput capped at one generation at a time. Opt-out via `KAS_GPU_SERIALIZE=0` (safe with one model). |
| **MLX on Apple Silicon only (platform-gated deps)** | Clean installs on Linux/Windows (no Apple packages). | No GPU inference on non-Apple hardware without llama.cpp/GGUF. | Requires explicit non-MLX backend for cross-platform. |
| **Context compaction (model-written summary)** | Sustained decode speed, avoids hard context overflow. | Loss of fine-grained transcript; model must re-learn from summary. | "Soft" compaction can be deferred to turn boundary; "hard" forces mid-tool-call. |
| **KV-cache persistence (delta files on disk)** | Warm resume across server restarts. | Disk I/O overhead; delta file management complexity. | Best-effort: failures fall back to cold prefill (`server/core/kvpersist.py`). |
| **Anthropic API compatibility (drop-in SDK)** | No client changes needed; works with official SDK. | Partial API surface (text + tool_use only; no files, messages API v2 features). | Unknown fields ignored (`server/schema.py:ConfigDict(extra="ignore")`). |
| **Sandboxed file tools (not bash)** | File operations confined to workdir. | Bash commands can access any filesystem path. | Explicitly documented: "bash is NOT sandboxed" (`agent/adapters/tools/executor.py`). |
| **Model registry (multi-model, LRU eviction)** | Multiple resident models, no swap-out-reload. | Memory bloat if many models loaded; budget + count cap required. | Active models cannot be evicted; over-cap loads can fail with 503 (`server/registry.py:_evict_to_make_room`). |
| **TUI (Textual, three-panel layout)** | Rich interactive experience: streaming, commands, themes. | Higher dependency footprint (Textual, Rich). | Experimental markdown UI (MDUI) gated off by default (`agent/tui/app.py:mdui="off"`). |

## 5. Findings ledger
| ID | Sev | Location | Rule | Finding | Fix | Effort | Status |
|----|-----|----------|------|---------|-----|--------|--------|
| F001 | Medium | `agent/adapters/tools/executor.py` | Security: least privilege | Bash tools are NOT sandboxed; file tools are. Users can execute arbitrary shell commands. | Document prominently; add optional bash sandboxing. | Low | Open |
| F002 | Low | `server/backends/mlx.py` | Reliability: error handling | MLX import failure surfaces a `RuntimeError` with actionable message; good. | None needed. | None | Closed |
| F003 | Low | `server/backends/llama_cpp.py` | Reliability: error handling | GGUF metadata read failures fall back to 0; KV restore plan is model-guarded. Good. | None needed. | None | Closed |
| F004 | Low | `server/app.py` | Security: input validation | Request body size limited to 64MB (`KAS_MAX_BODY_BYTES`); Pydantic validation enforced. | None needed. | None | Closed |
| F005 | Medium | `agent/cli.py` | Operational: lifecycle | `_spawn_server` uses `subprocess.Popen` with `start_new_session=True`; `lsof` preflight in `Makefile` and `server/cli.py` prevents port conflicts. | None needed. | None | Closed |
| F006 | Low | `server/registry.py` | Performance: memory management | GPU memory budgeting uses `.safetensors` file sizes; estimates can be rough for split models. | Add GGUF size estimation as fallback. | Medium | Open |
| F007 | Low | `agent/core/compaction.py` | Performance: compaction triggers | "Hard" limit at 85% of context window; "soft" triggers on decode rate < frac of baseline. | None needed. | None | Closed |
| F008 | Low | `server/core/pipeline.py` | Reliability: keep-alive | Wall-clock pings every 5s during silent prefill/tool-call buffering. | None needed. | None | Closed |
| F009 | Medium | `agent/adapters/storage/filesystem.py` | Reliability: session storage | Sessions stored under `~/.kas/sessions/`; best-effort; no WAL. | Add WAL or atomic writes for crash safety. | Medium | Open |
| F010 | Low | `server/adapters/http/sse.py` | Reliability: streaming | SSE frames with `text/event-stream`; handles tool_use blocks, thinking, text, pings. | None needed. | None | Closed |

## 6. Risks & non-risks
- **Risk:** GPU watchdog kill (macOS) — if two models submit overlapping Metal command buffers, the GPU watchdog (~17s) triggers an uncatchable C++ abort that kills the entire server. **Mitigated** by `GPU_LOCK` serializing all GPU work across all backends (`server/backends/_gpu.py`).
- **Risk:** Stale server holding GPU/port — if a server crashes but its process (or child) survives, it holds the port and GPU memory. **Mitigated** by `lsof` preflight in `Makefile` and `server/cli.py`, and `_pids_on_port` in `agent/cli.py` for `--stop`.
- **Risk:** Context overflow (garbage output) — sailing past the model's trained context length yields garbage. **Mitigated** by "hard" compaction at 85% of context window (`agent/core/compaction.py:HARD_LIMIT_FRAC`).
- **Risk:** GPU memory exhaustion (multi-model co-residency) — loading too many models simultaneously exceeds GPU memory, tripping the Metal command-buffer timeout. **Mitigated** by GPU budget (`KAS_GPU_BUDGET_GB`) and count cap (`KAS_MAX_MODELS`) in `server/registry.py:_evict_to_make_room`.
- **Non-risk:** Network egress — nothing leaves the machine; server listens on 127.0.0.1 by default (`server/cli.py`), and the client checks `_is_local_url` before auto-starting a server (`agent/cli.py`).
- **Non-risk:** Model weight downloads — models are downloaded once (with progress) to `~/.cache/huggingface/hub` and reused; no per-request downloads.
- **Strongest rejected alternative:** Running inference in-process (no separate server). Rejected because: (1) MLX GPU streams are bound to the creating thread; (2) FastAPI's thread pool cannot run MLX generation; (3) a separate server allows the TUI and CLI to connect via standard HTTP, enabling multi-client scenarios.

## 7. Verdict & recommendation
**Verdict:** **Active** — The system is production-grade for local agentic development on Apple Silicon and NVIDIA hardware. It handles GPU serialization, context compaction, KV-cache persistence, and multi-model registry robustly. The hexagonal architecture is clean, with clear separation between ports (protocols), adapters (concrete implementations), and core (domain logic).

**One next step:** Add optional bash sandboxing (currently explicitly not sandboxed per `agent/adapters/tools/executor.py`). This is the highest-impact security improvement, as users can currently execute arbitrary shell commands. A chroot or Docker container wrapper for bash tools would provide defense-in-depth without breaking existing workflows.