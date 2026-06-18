# Enhancement: standardized tool dispatcher (A2A-style)

Status: **parked / idea** — not scheduled. Captured for later.

## Core idea

The LLM is given a **fixed, tiny set of tools** — the *only* hardcoded schemas
it ever sees:

- **`dispatch-skill`** — invoke a skill/tool/agent by `id` with an arbitrary
  input payload. Returns either a synchronous result or an async **task handle**.
- **`dispatch-status`** — query a running dispatch by task id (for long /
  async skills).
- **`dispatch-cancel`** — cancel a running dispatch by task id.

Everything else — every real tool (`bash`, `read_file`, `generate_image`, …),
every sub-agent, every external MCP/A2A endpoint — lives **behind** the
dispatcher as a registered **skill**, described by a **card** (à la A2A *agent
cards*): `id`, description, input schema, optional output schema, sync/async,
cost/latency hints. The model **discovers** skills by reading cards, **not** by
having their schemas injected into its tool list.

Analogy: A2A = agent cards (capability discovery) + task lifecycle
(submit / status / cancel). This mirrors it at the tool layer: skill cards +
`dispatch` / `dispatch-status` / `dispatch-cancel`.

## Why this shape (the payoff)

1. **Stable LLM tool surface → cache-stable.** The advertised tool block never
   changes as capabilities are added/removed. The continuation memo's cache key
   depends on `tools` being identical across turns (see
   `server/core/continuation.py` + the "stable per session so the cache key
   holds" note in `agent/core/loop.py`). With only 3 dispatch tools, that block
   is frozen forever — new capability = new **card**, zero prompt-tool churn,
   zero KV-cache invalidation. This is the key win over both static per-tool
   injection (schema bloat) and naive dynamic discovery (re-prefill every turn).
2. **Tiny prompt.** 3 tools instead of N → less prefill, less model confusion
   when the catalog is large (many MCP servers, sub-agents, etc.).
3. **First-class async / long-running.** `status` + `cancel` handle slow skills
   (image gen, builds, sub-agents, remote A2A agents) without blocking the loop.
4. **Uniformity.** Tools, skills, and sub-agents all become "dispatchable
   skills" behind one interface. `subagent`, `generate_image`, `web_search`
   collapse into skills with cards + `requires` gating.

## Sketch

```
LLM tools (frozen):  dispatch-skill(id, input)  ·  dispatch-status(task)  ·  dispatch-cancel(task)

         dispatch-skill("generate_image", {...})
LLM ───────────────────────────────────────────▶  Dispatcher
                                                      │  validate input vs skill card's input_schema
                                                      │  sync → run + return; async → task id
                                                      ▼
                                            Skill registry / cards
                                  ┌───────────────┬───────────────┬──────────────┐
                                  │ local tools   │ sub-agents    │ MCP / A2A     │
                                  │ (bash, files, │ (art director,│ remote skills │
                                  │  image, web)  │  …)           │ + agents      │
                                  └───────────────┴───────────────┴──────────────┘
```

- **Discovery.** A compact **skills index** (one-line cards) is cheaply
  available — either a stable system-prompt section or a `dispatch-skill("skills",
  {query})` lookup. Full card (with `input_schema`) fetched on demand before
  dispatch, so the model can form a valid payload without the schema living in
  its tool definitions.
- **Validation.** The dispatcher validates the payload against the target
  skill's `input_schema` at call time and returns structured validation errors
  so the model self-corrects. (Server already type-coerces Qwen args — same
  spirit, centralized.)
- **Output.** Sync skills return content (text/image path) as today. Async
  skills return a task id; the model polls `dispatch-status`. Typed
  `output_schema` enables programmatic skill→skill chaining without the model in
  the loop (toward deterministic mini-workflows).

## Open questions

- **Discovery cost.** Reading cards adds a step before dispatch. Mitigate with
  an always-present one-line skills index; only fetch full cards on demand.
- **Payload correctness without injected schema.** The model forms free-form
  JSON validated server-side; the card's `input_schema` must be readable at/just
  before dispatch. Index could embed minimal schemas, or add a `describe-skill`.
- **Card freshness vs cache.** The *index* surfaced to the model is itself
  prompt content — keep it stable per session (discover-then-pin) so it doesn't
  re-invalidate the cache; refresh only on explicit `/tools` actions.
- **Errors / partial results / streaming** for async skills (task model).
- **Relationship to MCP/A2A.** Make skill cards MCP/A2A-compatible so remote
  servers' tools and remote agents register as skills for free.

## Fit / sequencing

Natural layer on the hexagonal tool seam (`ports/tools.py` already abstracts
`ToolExecutor`). Sequence after the v2 features land and ideally after the
plain tool-registry step (tools-as-data) — the dispatcher sits on top of a
registry. Changes how every tool is authored + how the model calls them, so
it's a deliberate vNext, not a bundle-in.
