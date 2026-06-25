from .base import Command


class PauseCommand(Command):
    name = "/pause"

    def run(self, app, arg: str) -> None:
        app.action_pause()
