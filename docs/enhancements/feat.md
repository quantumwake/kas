# kascode — activity tracker

One running checklist. Work items top-to-bottom; check them off as they land.
Deep-dive designs live in the sibling docs (linked). Updated as we go.

## ✅ Done (merged to `main`)
- [x] Hexagonal refactor (server + agent → core/ports/adapters)
- [x] `/ctx` context controls + safe-boundary compaction (no mid-write compaction)
- [x] `--sandbox` file-tool jail
- [x] KV cache-cliff fix (quantized caches)
- [x] `generate_image` tool (`--art`) + optional `web`/`art` extras
- [x] KV-resume — incremental on-disk KV, default on, `/kv`
- [x] Cancellable prefill + `POST /v1/cancel` (Esc stops a long prefill)
- [x] Subagent round-budget (parent-set, hard cap, soft-landing nudge)
- [x] Bash-livelock guard (escalating wait + auto-detach)
- [x] Reactive `/fx` (state-driven palettes/effects; plasma/scanline/fire/…)
- [x] Model picker shows size + partial/full
- [x] Repo rename `kascli → kascode`

## 🔧 In flight (open PRs / branches)
- [ ] `/stats` panel — PR #4 (`feat/stats`); awaiting a terminal eyeball → merge
- [ ] Banner polish — `feat/polish` (this) — warm gradient glow
- [ ] Async art — `feat/async-art` — fire-and-continue `generate_image` + `image_status`

## ⬜ Queued (build next, roughly in order)
- [ ] Async art (finish): background render, return task id + path, `image_status`
- [ ] Image/audio **analysis** — Whisper transcribe tool (simple; whisper models present); VLM image input (bigger)
- [ ] Voice interface — push-to-talk: mic → Whisper STT → agent → macOS `say` TTS
- [ ] Embeddings endpoint (`/v1/embeddings`) → hybrid vector RAG (rag.py left the seam)
- [ ] Frontier **reviewer** — headless `claude -p` judges the diff at turn end (see [models.md](models.md))
- [ ] `/model` multi-model — "offload vs load both" with size/OOM expectations
- [ ] Quantized-KV persistence (make warm-resume help long contexts)
- [ ] Batched concurrency — parallel requests on one GPU (vLLM-style)
- [ ] Live subagent split-screen pane (see [tui.md](tui.md))

## 🅿️ Parked (vision / platform — deep dives)
- [ ] Tool dispatcher (A2A-style `dispatch-skill`) — [tools.md](tools.md)
- [ ] Skills/plugins (executable), self-authoring, `/supercharge` — [skills.md](skills.md)
- [ ] Frontier model access (pluggable backend) — [models.md](models.md)
- [ ] Multimodal serve: image-out / embeddings endpoints + adapters — [multimodal.md](multimodal.md)

## Notes
- Reference: `~/Development/quantumwake/ai-test-bench` — existing crude A2A agents (Go).
- "Do the simple thing": image/embeddings as **typed endpoints/tools**, not jammed into the text token API.
