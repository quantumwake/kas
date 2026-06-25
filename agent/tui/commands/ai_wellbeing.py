from rich.text import Text

from .base import Command


class AiWellbeingCommand(Command):
    name = "/ai-wellbeing"

    def run(self, app, arg: str) -> None:
        if app.busy:
            app.body_write(Text("[/ai-wellbeing: wait until the agent is idle]", style="yellow"))
        elif not app.messages:
            app.body_write(Text("[ai-wellbeing: no conversation yet to assess]", style="yellow"))
        else:
            app.msg_q.put("\x00ai-wellbeing")
