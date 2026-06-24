"""TuiIO — the AgentIO port implementation for the TUI.

core.agent_turn runs on a worker thread; this marshals its stream/tool/notice
callbacks onto the Textual UI thread (via app.call_from_thread) and carries the
cross-thread control channels (steering queue, confirm queue, abort/pause
events). It talks to the app by duck-typed attribute access only.
"""

import json
import queue
import threading
import time
from typing import TYPE_CHECKING

from rich.text import Text

if TYPE_CHECKING:
    from .app import AgentApp


class TuiIO:
    """core.agent_turn IO interface, marshalling from the agent thread to the UI."""

    def __init__(self, app: "AgentApp") -> None:
        self.app = app
        self.steer_q: queue.Queue[str] = queue.Queue()
        self.confirm_q: queue.Queue[str] = queue.Queue()
        self.abort = threading.Event()
        self.pause = threading.Event()
        self.last_decode_tps: float = 0.0
        self._line = ""
        self._kind = "text"
        self._t0 = 0.0
        self._ttft: float | None = None

    def _ui(self, fn, *args) -> None:
        try:
            self.app.call_from_thread(fn, *args)
        except Exception:
            pass  # app shutting down

    def _write(self, text: str, style: str = "") -> None:
        self._ui(self.app.body_write, Text(text, style=style))

    def _flush_line(self) -> None:
        if self._line:
            self._write(self._line, "dim italic" if self._kind == "thinking" else "")
            self._line = ""

    # ---- interface called by core.agent_turn (agent thread) ----

    def stream_started(self) -> None:
        self._t0, self._ttft = time.time(), None

    def delta(self, kind: str, text: str) -> None:
        if self._ttft is None:
            self._ttft = time.time() - self._t0
        if kind != self._kind:
            self._flush_line()
            self._kind = kind
        self._line += text
        while "\n" in self._line:
            line, self._line = self._line.split("\n", 1)
            self._write(line, "dim italic" if kind == "thinking" else "")

    def stream_finished(self, usage) -> None:
        self._flush_line()
        if usage is not None:
            decode_t = max(0.05, (time.time() - self._t0) - (self._ttft or 0))
            self.last_decode_tps = usage.output_tokens / decode_t
            # cumulative session token totals, for the /stats panel
            self.app.tok_in += usage.input_tokens
            self.app.tok_out += usage.output_tokens
            self._write(
                f"[{usage.input_tokens} in / {usage.output_tokens} out · "
                f"ttft {self._ttft or 0:.1f}s · {self.last_decode_tps:.1f} tok/s · "
                f"total {time.time() - self._t0:.1f}s]",
                "dim",
            )

    def tool_call(self, name: str, args: dict) -> None:
        self._flush_line()
        self._write(f"→ {name}({json.dumps(args, ensure_ascii=False)[:200]})", "bold cyan")

    def tool_result(self, output: str, is_error: bool) -> None:
        preview = output if len(output) < 300 else output[:300] + "..."
        mark, style = ("✗", "red") if is_error else ("✓", "green")
        self._write(f"  {mark} {preview}", style)

    def notice(self, text: str) -> None:
        self._flush_line()
        self._write(text, "yellow")

    def confirm(self, command: str) -> str:
        self._ui(self.app.enter_confirm, command)
        answer = self.confirm_q.get()  # blocks the agent thread, UI stays live
        self._ui(self.app.exit_confirm)
        return answer.strip().lower()

    def drain_steers(self) -> list[str]:
        out: list[str] = []
        while True:
            try:
                out.append(self.steer_q.get_nowait())
            except queue.Empty:
                return out

    def should_abort(self) -> bool:
        return self.abort.is_set()

    def should_pause(self) -> bool:
        return self.pause.is_set()

    def clear_abort(self) -> None:
        self.abort.clear()

    # subagent lifecycle → app registry (for /subagents + drill-in)
    def subagent_started(self, sub) -> None:
        self._ui(self.app.register_subagent, sub)

    def subagent_finished(self, sub, ok: bool) -> None:
        self._ui(self.app.refresh_status)
