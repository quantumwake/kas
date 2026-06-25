"""/memory — inspect and search local recall (code / docs / session memory).

  /memory               status: backends, indexed sources + counts, db size
  /memory on | off      toggle whether the agent can call the recall tool
  /memory search <q>    run a recall query and show the hits in the TUI

`/rag` is kept as a (deprecated) alias for the same command.
"""

from rich.text import Text

from .base import Command


class MemoryCommand(Command):
    name = "/memory"
    summary = "inspect & search local memory (code / docs / sessions)"
    usage = "[on|off|search <q>]"
    subcommands = (
        ("search", "run a recall query and show hits — /memory search <q>"),
        ("on", "let the agent use the recall tool"),
        ("off", "disable the recall tool"),
    )

    def match(self, text: str) -> str | None:
        # prefix match so "/memory search ..." and the /rag alias both route here
        return text[len(self.name) :] if text.startswith(self.name) else None

    def run(self, app, arg: str) -> None:
        arg = arg.strip()
        low = arg.lower()
        if low in ("on", "enable"):
            app.runner.rag = True
            self._status(app)
        elif low in ("off", "disable"):
            app.runner.rag = False
            self._status(app)
        elif low.startswith("search"):
            query = arg[len("search") :].strip()
            if not query:
                app.body_write(Text("usage: /memory search <query>", style="yellow"))
                return
            app.body_write(Text("[memory: indexing + searching…]", style="dim"))
            self._run_off_thread(app, lambda: app.runner.memory.search_lines(query))
        elif low in ("", "status"):
            app.body_write(Text("[memory: indexing…]", style="dim"))
            self._run_off_thread(app, lambda: app.runner.memory.status_lines(app.runner.rag))
        else:
            app.body_write(Text("usage: /memory [on|off|search <q>]", style="yellow"))

    @staticmethod
    def _status(app) -> None:
        app.body_write(Text("[memory: indexing…]", style="dim"))
        MemoryCommand._run_off_thread(app, lambda: app.runner.memory.status_lines(app.runner.rag))

    @staticmethod
    def _run_off_thread(app, produce) -> None:
        """Indexing can take a beat on a cold index — do it off the UI thread and
        marshal the rendered (text, style) rows back via call_from_thread."""
        import threading

        def work() -> None:
            try:
                rows = produce()
            except Exception as exc:  # never crash the UI thread
                rows = [(f"memory: {type(exc).__name__}: {exc}", "red")]
            for text, style in rows:
                try:
                    app.call_from_thread(app.body_write, Text(text, style=style))
                except Exception:
                    pass

        threading.Thread(target=work, daemon=True).start()


class RagCommand(MemoryCommand):
    """Deprecated alias for /memory (the flag is still `runner.rag` internally)."""

    name = "/rag"
    summary = "→ alias for /memory"
    usage = ""
    subcommands = ()

    def completions(self) -> list[str]:
        return ["/rag"]  # keep the menu/Tab clean — subcommands live under /memory
