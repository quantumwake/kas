"""/converse — hands-free voice conversation with the agent (turn-based).

Loop: listen (VAD ends the turn when you stop talking) → transcribe → show it →
run the normal agent turn → speak the reply → listen again. Strictly one party
at a time: it won't listen while thinking or speaking, so you don't trip over
each other.

Ends on any of: a spoken stop word (stop/cancel/exit/pause/…), Escape, /converse
again, or ~15s of nobody talking. Replies are kept short + spoken (a voice
directive on the first turn); full barge-in / interruption is a later phase.
"""

import threading
import time

from rich.text import Text

from ...adapters.audio.stt import preload, whisper_available
from ._voice import NO_SPEECH, listen_once, note
from .base import Command

VOICE_DIRECTIVE = (
    "\n\n[You are in a live VOICE conversation. Reply in 1–2 short, natural "
    "spoken sentences — no markdown, no code blocks, no lists, just talk. Do any "
    "needed tool work quietly and report the result in one sentence.]"
)
STOP_PHRASES = {
    "stop", "stop listening", "cancel", "exit", "exit voice", "pause", "quit",
    "end conversation", "goodbye",
}
MAX_TURN_SECS = 30  # a single spoken turn can't exceed this
NO_SPEECH_SECS = 15.0  # silence this long with nobody talking ends the conversation


class ConverseCommand(Command):
    name = "/converse"
    summary = "hands-free voice conversation with the agent (turn-based)"
    usage = "(toggle)"

    def run(self, app, arg: str) -> None:
        if getattr(app, "converse", False):  # already running -> stop
            app.converse = False
            app.body_write(Text("[stopping voice conversation…]", style="yellow"))
            return
        if not whisper_available():
            app.body_write(
                Text("voice→text needs mlx-whisper — run `/listen install`", style="yellow")
            )
            return
        app.converse = True
        app.tts_on = True  # speak replies
        app.body_write(
            Text(
                "🎙 voice conversation ON — just talk. Ends on 'stop'/'cancel', "
                "Escape, /converse, or 15s of silence.",
                style="cyan",
            )
        )
        threading.Thread(target=lambda: self._loop(app), daemon=True).start()

    # -- the loop ------------------------------------------------------------

    def _loop(self, app) -> None:
        threading.Thread(target=preload, daemon=True).start()  # warm the model now
        first = True
        reason = "/converse"
        try:
            while getattr(app, "converse", False):
                if not self._await_idle(app):
                    reason = "stopped"
                    break
                text, err = listen_once(
                    app, MAX_TURN_SECS, vad=True,
                    silence_limit=NO_SPEECH_SECS, should_stop=lambda: not app.converse,
                )
                if not app.converse:
                    reason = "stopped"
                    break
                if err == NO_SPEECH:
                    reason = f"{int(NO_SPEECH_SECS)}s of silence"
                    break
                if err:  # "cancelled" or a real mic error
                    reason = "mic error" if err != "cancelled" else "stopped"
                    if err not in ("cancelled",):
                        note(app, err, "red")
                    break
                text = text.strip()
                if len(text) < 2:
                    continue  # heard a blip, nothing intelligible — keep listening
                if text.lower().strip(" .!?") in STOP_PHRASES:
                    reason = f"heard '{text.strip()}'"
                    break
                note(app, f"🗣  {text}", "bold #3fb950")
                app.msg_q.put(text + (VOICE_DIRECTIVE if first else ""))
                first = False
                self._await_turn(app)
        finally:
            app.converse = False
            app.tts_on = False
            app.voice_indicator(None)
            note(app, f"🛑 voice conversation ended ({reason})", "yellow")

    # -- turn coordination (no tripping over each other) ---------------------

    @staticmethod
    def _speaking(app) -> bool:
        ov = getattr(app, "fx_override", None)
        return bool(ov and ov.get("mode") == "speaking")

    def _await_idle(self, app) -> bool:
        """Block until the agent is idle and not speaking. False if stopped."""
        while app.busy or self._speaking(app):
            if not app.converse:
                return False
            time.sleep(0.1)
        return app.converse

    def _await_turn(self, app) -> None:
        """After submitting, wait for the turn to START, finish, and stop speaking
        — so we never listen on top of the agent answering/speaking the previous
        turn (which would bleed its voice into the next capture).

        The message is queued, so it WILL be picked up; we wait for busy to go
        True without a short timeout (only Escape/stop bails). A generous cap
        guards against a wedged agent loop. We also accept a turn that finished so
        fast we missed the busy flag (turns counter moved)."""
        turns0 = getattr(app, "turns", 0)
        t0 = time.monotonic()
        while not app.busy:
            if not app.converse or getattr(app, "turns", 0) != turns0:
                return  # stopped, or the turn already came and went
            if time.monotonic() - t0 > 120:
                return  # agent loop looks wedged — don't hang forever
            time.sleep(0.03)
        while app.busy:
            if not app.converse:
                return
            time.sleep(0.1)
        while self._speaking(app):
            if not app.converse:
                return
            time.sleep(0.1)
