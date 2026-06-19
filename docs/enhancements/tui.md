# Enhancement: live subagent visibility — split-screen

Status: **parked / idea** — not scheduled. Captured for later.

Want: see what live subagents are doing *right in the TUI*, ideally in a
split pane you can drag open with the mouse (iTerm-style).

## Today
- Subagents capture full output to `SubagentIO.buffer`; only compact markers
  leak to the main view.
- `/subagents` lists them; `/subagent <n>` opens a read-only modal of one's
  transcript (Esc closes it). So drill-in exists, but it's *after the fact* and
  modal, not a live side-by-side.

## Target (two parts, very different cost)

### A. Live subagent pane — *moderate*, do this first
- A toggleable second pane (e.g. `/split` or a key) showing the **active**
  subagent's output streaming live.
- Wiring: `SubagentIO.delta/tool_call` already capture to a buffer; also push
  to a live `RichLog` pane via `app.call_from_thread` (subagent runs on the
  worker thread). Layout = a `Horizontal` split: main work view | subagent pane.
- Resize via keys (e.g. `[` / `]` or arrow) — cheap, no mouse needed.
- Picks the most-recent running subagent, or `/split <n>` for a specific one.

### B. Mouse-drag-to-split divider — *complex*, the part to defer
- Textual has **no built-in draggable splitter**. You'd build a 1-col/1-row
  "Splitter" widget that captures `MouseDown` → `MouseMove` → adjusts the
  fractional widths of the adjacent panes → `MouseUp`. Plus hit-testing, min
  sizes, and persisting the ratio. Doable but fiddly and easy to make janky.
- Recommendation: ship A with keyboard resize; only attempt B if the live pane
  proves useful enough to warrant the polish.

## Notes
- Multiple concurrent subagents are *serialized* on the single GPU worker
  (see the engine), so "live" means one active subagent at a time anyway —
  a single pane is sufficient; no need for N panes.
- Keep it opt-in (off by default) so the default single-pane view is unchanged.
