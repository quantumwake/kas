"""/memory — inspect, search, and manage local recall (code / docs / sessions).

/memory                  status: stores, platform/install/enabled state, embedders
/memory on | off         toggle whether the agent can call the recall tool
/memory search <q>       run a recall query and show the hits in the TUI
/memory reindex [full]   rescan changed files (full = wipe + rebuild)
/memory clear            drop the indexes, leaving the stores empty
/memory enable  <store>  turn a store on   (persisted to ~/.kascode/memory.json)
/memory disable <store>  turn a store off
/memory install vector [fmt]   install the vector store + an embedder format
                               (fmt: model2vec [default] | mlx | gguf, chip-gated)
"""

import subprocess
import threading

from rich.text import Text

from .base import Command


class MemoryCommand(Command):
    name = "/memory"
    summary = "inspect, search & manage local memory stores"
    usage = "[on|off|search|reindex|clear|enable|disable|install]"
    subcommands = (
        ("search", "run a recall query and show hits — /memory search <q>"),
        ("reindex", "rescan changed files (or 'reindex full' to rebuild)"),
        ("clear", "drop the indexes, leaving the stores empty"),
        ("enable", "turn a store on — /memory enable <store>"),
        ("disable", "turn a store off — /memory disable <store>"),
        ("install", "install a store + embedder — /memory install vector [model2vec|mlx|gguf]"),
        ("on", "let the agent use the recall tool"),
        ("off", "disable the recall tool"),
    )

    def match(self, text: str) -> str | None:
        # prefix match so "/memory search ..." (with an arg) routes here too
        return text[len(self.name) :] if text.startswith(self.name) else None

    def run(self, app, arg: str) -> None:
        arg = arg.strip()
        verb, _, rest = arg.partition(" ")
        verb, rest = verb.lower(), rest.strip()
        if verb in ("on", "enable") and not rest:
            app.runner.rag = True
            self._status(app)
        elif verb in ("off", "disable") and not rest:
            app.runner.rag = False
            self._status(app)
        elif verb in ("enable", "disable"):
            self._toggle(app, rest, on=verb == "enable")
        elif verb == "install":
            self._install(app, rest)
        elif verb == "reindex":
            full = rest.lower() in ("full", "rebuild", "all")
            app.body_write(
                Text(f"[memory: {'rebuilding' if full else 'reindexing'}…]", style="dim")
            )
            self._off_thread(app, lambda: app.runner.memory.reindex_lines(full))
        elif verb == "clear":
            app.body_write(Text("[memory: clearing indexes…]", style="dim"))
            self._off_thread(app, lambda: app.runner.memory.clear_lines())
        elif verb == "search":
            if not rest:
                app.body_write(Text("usage: /memory search <query>", style="yellow"))
                return
            app.body_write(Text("[memory: indexing + searching…]", style="dim"))
            self._off_thread(app, lambda: app.runner.memory.search_lines(rest))
        elif verb in ("", "status"):
            self._status(app)
        else:
            app.body_write(
                Text(
                    "usage: /memory [on|off|search|reindex|clear|enable|disable|install]",
                    style="yellow",
                )
            )

    # -- subcommands ----------------------------------------------------------

    @staticmethod
    def _status(app) -> None:
        app.body_write(Text("[memory: indexing…]", style="dim"))
        MemoryCommand._off_thread(app, lambda: app.runner.memory.status_lines(app.runner.rag))

    @staticmethod
    def _toggle(app, name: str, on: bool) -> None:
        from agent.adapters.retrieval.stores import STORES, set_enabled

        if name not in STORES:
            app.body_write(Text(f"unknown store {name!r} — have: {', '.join(STORES)}", style="red"))
            return
        set_enabled(name, on)
        app.runner.memory._instances.clear()  # rebuild active set next call
        app.body_write(Text(f"store {name} {'enabled' if on else 'disabled'}", style="green"))
        MemoryCommand._status(app)

    @staticmethod
    def _install(app, rest: str) -> None:
        # /memory install [<store>] [<embedder-format>]   (defaults: vector, model2vec)
        parts = rest.split()
        store = parts[0] if parts else "vector"
        embedder = parts[1] if len(parts) > 1 else None
        from agent.adapters.retrieval.stores import install_command

        cmd, err = install_command(store, embedder)
        if cmd is None:
            app.body_write(Text(f"can't install: {err}", style="yellow"))
            return
        label = store + (f" ({embedder})" if embedder else "")
        app.body_write(Text(f"[installing {label}: {' '.join(cmd)} …]", style="yellow"))

        def work() -> None:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                ok = proc.returncode == 0
                tail = (proc.stdout + proc.stderr).strip().splitlines()[-4:]
                for line in tail:
                    app.call_from_thread(app.body_write, Text(f"  {line}", style="dim"))
                if ok:
                    import importlib

                    importlib.invalidate_caches()  # so find_spec sees the new packages
                    app.runner.memory._instances.clear()  # re-resolve embedder/availability
                    app.call_from_thread(
                        app.body_write,
                        Text(f"[{label} installed — /memory to verify]", style="green"),
                    )
                    app.call_from_thread(
                        app.body_write, Text("[restart kas if it doesn't light up]", style="dim")
                    )
                else:
                    app.call_from_thread(
                        app.body_write,
                        Text(f"[install of {label} failed — see above]", style="red"),
                    )
            except Exception as exc:
                app.call_from_thread(
                    app.body_write,
                    Text(f"[install error: {type(exc).__name__}: {exc}]", style="red"),
                )

        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _off_thread(app, produce) -> None:
        """Indexing can take a beat on a cold index — do it off the UI thread and
        marshal the rendered (text, style) rows back via call_from_thread."""

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
