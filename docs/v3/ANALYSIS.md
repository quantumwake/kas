# kas v3 — Independent Analysis

> A second-pass technical analysis of **kas** (Kasra's Agentic Shell), produced
> by re-deriving the claims in `docs/reports/` against the actual code rather
> than trusting them. Where the existing reports are right, this says so; where
> they are wrong or soft, it corrects them. This is the factual basis for
> [`PLAN.md`](./PLAN.md).
>
> **Method:** every load-bearing claim was checked against source. Statistics
> come from an AST scan of the tree (not estimates). The sandbox behaviour was
> verified empirically (a live symlink-escape test). Two structural maps
> (`tui.py`, ports/core coupling) were produced by dedicated read-only passes.

---

## 1. Verdict on the existing reports

The `docs/reports/` set is **accurate where it counts and well-evidenced** — it
is a real review of real code, not a hallucination. Caveats:

| Issue | Severity | Status |
|-------|----------|--------|
| "Symlink vulnerability" (security §4) was **factually wrong** — `resolve()` canonicalizes symlinks, then checks containment, so an escaping symlink is *rejected*. Verified empirically. | High (a false vuln erodes trust) | **Fixed in place** in `security-assessment.md` + `executive-summary.md` |
| Grade inflation — all 18 criteria land 3–5; tone is congratulatory ("exemplary", "a pleasure to review"). | Medium | Re-scored below with a sharper edge |
| "~47 Python files" | Low | Actual: **68** files, 7,486 LOC |
| "Weighted average" scoring | Low | No weights are defined; the numbers are plain means dressed as quantitative |

Everything else verified true: file sizes, `shell=True`, unauthenticated
endpoints, unbounded `max_tokens`, the sandbox resolver code, the test layout.

---

## 2. Architecture — the hexagonal claim is real (mostly)

**Verified clean:** an import scan finds **zero** imports of `*.adapters.*`
inside `agent/core/` or `server/core/`. The core depends only on Protocols:

- `agent/ports/ui.py` → `AgentIO` (`@runtime_checkable`, 11 methods + `last_decode_tps`)
- `agent/ports/tools.py` → `ToolExecutor` (`run`, `checkpoint`, + `net`/`rag`/`context_limit` flags)
- `server/core/ports.py` → `EngineLike`, `DialectLike`

This is a genuinely correct ports/adapters core. The gaps are at the **edges**:

| Gap | Detail | Why it matters |
|-----|--------|----------------|
| **Duck-typed UI port** | `TuiIO` (tui.py) and `ConsoleIO` implement `AgentIO` structurally but neither *declares* it. `AgentIO` is `@runtime_checkable` yet conformance is never asserted. | A missing/renamed method on `TuiIO` fails at runtime mid-session, not at startup. |
| **Unported composition deps** | `SessionStore` (storage) and `GitWorkspace` (workspace) are instantiated in `cli.py` with no port interface. | Core/composition reach into concrete classes; no seam for alternatives or fakes → these are exactly the modules with **0 test coverage**. |
| **Fat tool adapter** | `ToolRunner` (executor.py, 312L) instantiates and dispatches ~15 tools (bash, files, recall, web, image, git) internally. | One class is the dispatcher *and* the per-tool glue. Acceptable hexagonally, but it's a complexity sink and hard to test piecewise. |

---

## 3. Complexity — hard numbers (AST scan, whole tree)

353 functions total. **18 exceed 50 lines; 9 exceed 80.** The worst offenders by
length **and** branch count (cyclomatic proxy):

| Lines | Branches | Location | Function |
|------:|---------:|----------|----------|
| **232** | **60** | `agent/core/loop.py:100` | `agent_turn()` — the agentic loop |
| **172** | 29 | `server/engine.py:285` | `generate()` — MLX inference orchestration |
| **167** | 38 | `agent/cli.py:119` | `main()` — arg parsing + wiring + dispatch |
| **153** | **55** | `agent/tui.py:1258` | `on_input_submitted()` — 14+ slash-command dispatcher |
| 133 | 24 | `server/core/pipeline.py:31` | `run()` — gen→events |
| 111 | 23 | `server/engine.py:344` | `produce()` |
| 108 | 9 | `server/adapters/http/sse.py:19` | `stream()` |
| 91 | 20 | `agent/cli.py:26` | `serve_main()` |
| 89 | 17 | `agent/core/compaction.py:109` | `compact_messages()` |

`agent_turn()` (60 branches) and `on_input_submitted()` (55 branches) are the two
cognitive-complexity hotspots. They are the priority targets — not because they
are long, but because their branch density makes them unsafe to change.

### `tui.py` (1,538 lines) — structural map

| Region | Lines | Note |
|--------|------:|------|
| `FxBar` | 639 | Ambient effects class; **48 effect methods** (~450L) — already modular, trivially extractable |
| `AgentApp` | 641 | App + command routing + 2 worker threads + stats + model-swap |
| `TuiIO` | 104 | The `AgentIO` adapter (duck-typed) |
| `ModelSelect`, `SubagentView`, `PasteInput`, `SelectableRichLog` | ~111 | Small widgets/modals |

Clean seams (no hidden coupling beyond shared `AgentApp` state): the 48 effects,
the slash-command dispatcher, the stats panel, the model-switch flow, and the two
worker loops (`_agent_loop`, `_status_loop`) can each move to their own module.

---

## 4. Security — the real risk ranking

The existing report identifies the right items but softens them with even 3–4
scores. Reframed by actual exposure:

1. **`shell=True` + `--yolo` + sandbox-off-by-default (the headline).** Three
   separate "gaps" that *combine* into: a prompt-injected model can run arbitrary
   commands anywhere the user can. Verified: `bash.py` uses
   `Popen(command, shell=True)`; `--sandbox` defaults off (`cli.py:142`,
   `KAS_SANDBOX==1` to enable); `--sandbox` does not constrain bash regardless.
   → **v3 makes sandbox default-on** (Plan Phase 1). Bash containment (timeout,
   `ulimit`, denylist) is a larger follow-up.
2. **No auth on any endpoint** — fine on localhost, a hole the moment someone
   binds `0.0.0.0`. Should be enforced/warned in code, not just documented.
3. **`max_tokens` has no upper bound** (`schema.py:61`, default 1024, no `le=`) and
   there is **no request-body size limit** — trivial local DoS / memory abuse.
4. **Path traversal is actually solid** (symlink claim retracted). The only real
   residual is bash's freedom to `cd` out — see #1.

Privacy/offline posture (5/5) is genuine and confirmed.

---

## 5. Tests — what's really there

- **7 hand-rolled assert scripts** (`tests/test_*.py`, 790 LOC) run as
  `python tests/test_x.py` via `make test`. **pytest is not installed**; there
  are no test functions/classes, no fixtures, no coverage measurement.
- The reported "~30–35% coverage" is a **guess** — it cannot be measured with the
  current harness. Treat it as unverified.
- **Zero coverage**, confirmed by reference scan, for: `bash.py`, `web.py`,
  `bm25.py`, `git.py`, `filesystem.py`, `loop.py`, `tui.py`. These overlap exactly
  with the unported adapters in §2 — untested *because* they have no seam.
- What is tested is tested well: parser (both dialects), continuation, cache,
  kvpersist, the file-tool sandbox, compaction policy, and a real-SDK API round-trip.

**Implication for v3:** we cannot safely split `agent_turn()` or `on_input_submitted()`
until characterization tests lock their current behaviour. Test-net first, refactor second.

---

## 6. Re-scored

Same 1–5 scale, less generous, same evidence:

| Dimension | Existing | This analysis | Why the delta |
|-----------|:--------:|:-------------:|---------------|
| Architecture (core) | 5 | **5** | Earned — core isolation is real |
| Architecture (edges/ports hygiene) | — | **3** | Duck-typed ports, unported composition deps |
| Security | 4.0 | **3.5** | The shell+yolo+sandbox triad is a single high risk, not three medium ones |
| Complexity | 4 | **3** | Two 50+ branch functions is not "Good" |
| Test coverage | 4 | **3** | Unmeasured; 7 critical modules at zero |
| Documentation | 5 | **5** | Genuinely excellent |
| Functionality | 4.3 | **4.3** | No change — it works and is complete |

**Bottom line:** a legitimately well-architected v0.1 with an exemplary core, held
back by (a) two unsafe-to-edit god-functions, (b) a 1,538-line TUI, (c) sandbox
defaulting off, and (d) no test net or quality tooling around the parts that need
changing most. All four are addressed in [`PLAN.md`](./PLAN.md).
