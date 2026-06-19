# Enhancement: frontier model access (pluggable backend + minimal-cost reviewer)

Status: **parked / idea** — not scheduled. Captured for later.

Goal: let the local agent optionally use a frontier model (Claude / Codex) while
**keeping the local MLX model as the workhorse** and frontier spend tiny. Two
layered integration points.

---

## 1. Pluggable backend (swap the brain)

kas already drives the Anthropic Messages API via the official SDK with a
configurable `--base-url`, so:

- **Claude** — point `--base-url https://api.anthropic.com` + a real key; the
  same TUI/tools/loop drive real Claude. Server-only bits (`x-agent-thread`, the
  continuation memo) are harmlessly ignored. Add a `--provider {local,claude,
  openai}` convenience so you don't hand-set base-url/key.
- **Codex / GPT** — OpenAI speaks Chat Completions, not Anthropic Messages.
  Either run an Anthropic-compatible **proxy** (e.g. LiteLLM) and point kas at it
  (zero agent code), or write a second `LLMClient` adapter.
- **Headless CLIs** — alternatively shell out to `claude -p` (print/JSON) or
  `codex exec`-style non-interactive runs as a backend; verify exact flags /
  output formats before building (they drift).

Hexagonal fit: a `LLMClient` port + per-provider adapters; selection per session
(and per-subagent — see below).

## 2. Frontier *reviewer* sub-agent (the cost-smart one)

Local model does the work; a frontier model **reviews** it at boundaries. Rests
on the doer/judge asymmetry: the doer spends thousands of round-trips, the judge
reads one diff. Frontier-grade oversight at a fraction of frontier cost, aimed at
the exact local-model failure modes (false "done" claims, unverified fixes,
"sprites exist" when they don't).

### Keep frontier calls minimal (all levers)
1. **Review diffs, not transcripts.** Reviewer payload = task statement + the
   **git diff** + the local model's own summary. Tiny, focused — not the live
   context. `GitWorkspace` already produces per-turn diffs (natural hook).
2. **Cadence = boundaries, not rounds.** Fire at **checkpoint/commit** and/or
   **end-of-task**, never per tool round. One frontier call per unit of work.
3. **Session cap + risk-gating.** Max N reviews/session; optionally only when the
   diff is non-trivial / touches risky files.
4. **Structured output → fix loop.** Reviewer returns `{file, line, severity,
   issue, fix}[]` or `LGTM`; the local model consumes it and patches. The
   frontier model never *writes* — it only *judges*.

### Trigger
- **Auto at the boundary** (reliable — the local model won't self-request review
  for the same reason it "assumes" it's done), plus an optional `request_review`
  tool the local model can call when genuinely unsure.

### Why reviewer > escalation
Escalation pays frontier rates to *do* hard work (many tokens). Review pays
frontier rates only to *check* (one diff). Local stays the workhorse. Escalation
can be added later for the rare cases review can't salvage.

### Fit
- Uses the `LLMClient` frontier adapter from (1).
- A loop step gated by `--review` that runs the frontier client on the diff at
  checkpoint/end-of-task and injects findings as a user turn.
- Generalizes later into a "reviewer skill" under the dispatch model
  (`docs/enhancements/tools.md`), but doesn't need it to ship.

---

## Cross-cutting
- **Offline-first gating.** Both layers leave the machine + cost money — opt-in,
  explicit (`--provider` / `--review` / `--escalate`), **off by default**. The
  fully-local mode stays the default identity.
- **Auth + cost surfacing.** User supplies keys/subscriptions; the agent should
  surface (and optionally confirm, like bash) when it's about to call frontier.
- **Sequencing.** Backend-swap (Claude) is almost free → small near-term win.
  The reviewer rides on it. Escalation + reviewer-as-dispatch-skill are vNext.

## Open questions
- Headless CLI invocation/output stability for `claude -p` / `codex`.
- Best risk heuristic for gating reviews (diff size? touched paths? local-model
  confidence signal?).
- Where review findings live in the transcript vs the cache key.
- Budget model: per-session token/cost cap shared with escalation.
