"""/models — list the models resident on the server (GPU memory + which is
active/default), and offload one with `/models unload <id|n>`.

Distinct from `/model` (singular), which switches the *default* served model.
The server keeps several models loaded at once (LRU + GPU budget); this is how
you see what's resident and free GPU memory by offloading idle ones.
"""

import httpx
from rich.text import Text

from .base import Command


class ModelsCommand(Command):
    name = "/models"
    summary = "list resident models + GPU memory; offload with `unload <id|n>`"
    usage = "[unload <id|n>]"

    def match(self, text: str) -> str | None:
        return text[len(self.name) :].strip() if text.startswith(self.name) else None

    def _loaded(self, app) -> list[dict] | None:
        try:
            data = httpx.get(app.base_url.rstrip("/") + "/v1/models", timeout=5).json()
            return [m for m in data.get("data", []) if m.get("id")]
        except Exception as exc:
            app.body_write(Text(f"could not reach the server: {exc}", style="red"))
            return None

    def run(self, app, arg: str) -> None:
        loaded = self._loaded(app)
        if loaded is None:
            return

        if arg.startswith("unload"):
            target = arg[len("unload") :].strip()
            ids = [m["id"] for m in loaded]
            if target.isdigit() and 1 <= int(target) <= len(ids):
                target = ids[int(target) - 1]
            if not target:
                app.body_write(Text("usage: /models unload <id|n>", style="yellow"))
                return
            try:
                r = httpx.post(
                    app.base_url.rstrip("/") + "/v1/models/unload",
                    json={"model": target},
                    timeout=30,
                ).json()
            except Exception as exc:
                app.body_write(Text(f"offload failed: {exc}", style="red"))
                return
            short = target.split("/")[-1]
            if r.get("ok"):
                app.body_write(Text(f"offloaded {short} — freed GPU memory", style="green"))
            else:
                app.body_write(
                    Text(f"could not offload {short}: {r.get('message')}", style="yellow")
                )
            return

        if not loaded:
            app.body_write(Text("no models loaded", style="yellow"))
            return
        t = Text()
        t.append("resident models:\n", style="bold")
        for i, m in enumerate(loaded, 1):
            gpu = m.get("gpu_active_gb") or m.get("est_gb")
            gb = f"{gpu:.1f} GB" if isinstance(gpu, int | float) else "? GB"
            tags = []
            if m.get("default"):
                tags.append("default")
            if m.get("active"):
                tags.append("active")
            suffix = f"  ({', '.join(tags)})" if tags else ""
            t.append(f"  {i}) {m['id']}  ·  {gb}{suffix}\n")
        t.append("offload an idle one:  /models unload <id|n>", style="bright_black")
        app.body_write(t)
