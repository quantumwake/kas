from rich.text import Text

from .base import Command


class SelfSkillCommand(Command):
    name = "/self-skill"

    def run(self, app, arg: str) -> None:
        if app.busy:
            app.body_write(Text("[/self-skill: wait until the agent is idle]", style="yellow"))
        else:
            app.msg_q.put("\x00self-skill")
