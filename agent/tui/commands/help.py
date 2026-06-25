from rich.text import Text

from .base import Command


class HelpCommand(Command):
    """The fallback for an unrecognised /command — never matched directly."""

    name = "/help"

    def run(self, app, arg: str) -> None:
        app.body_write(
            Text(
                "commands: /spec  /yolo  /rag [enable|disable]  /ctx [<n>|max|auto]  /subagents  "
                "/subagent <n>  /status  /compact  /self-skill  /ai-wellbeing  /model  /fx  "
                "/theme  /sandbox  /stop (Esc)  /pause (^P) · exit",
                style="yellow",
            )
        )
