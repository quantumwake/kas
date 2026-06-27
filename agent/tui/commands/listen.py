"""/listen [seconds] — record from the mic, transcribe, and submit to the agent."""

import threading

from rich.text import Text
from textual.widgets import Input

from ...adapters.audio.stt import preload, whisper_available
from ._voice import listen_once, note
from .base import Command


class ListenCommand(Command):
    name = "/listen"
    summary = "record from the mic, transcribe, and send to the agent (voice→text)"
    usage = "[seconds|install]"
    subcommands = (("install", "install mlx-whisper for voice→text"),)

    def run(self, app, arg: str) -> None:
        if arg.strip().lower() == "install":
            from ._install import install_capability

            install_capability(app, "voice")
            return
        if not whisper_available():
            app.body_write(
                Text("voice→text needs mlx-whisper — run `/listen install`", style="yellow")
            )
            return
        secs = max(1, min(int(arg) if arg.strip().isdigit() else 5, 120))
        app.body_write(Text(f"🎙  listening for {secs}s…", style="cyan"))
        threading.Thread(target=preload, daemon=True).start()  # warm during recording
        threading.Thread(target=lambda: self._worker(app, secs), daemon=True).start()

    def _worker(self, app, secs: int) -> None:
        text, err = listen_once(app, secs, vad=False)
        if err:
            note(app, err, "red")
        elif not text:
            note(app, "(heard nothing)", "yellow")
        else:
            self._submit(app, text)

    @staticmethod
    def _submit(app, text: str) -> None:
        """Auto-submit the transcript as a turn (combining any text already typed
        in the box), so a single /listen goes straight to the agent."""

        def do() -> None:
            inp = app.query_one(Input)
            full = f"{inp.value} {text}".strip() if inp.value else text
            inp.value = ""
            app._submit_message(full)

        try:
            app.call_from_thread(do)
        except Exception:
            pass
