from .base import Command


class StopCommand(Command):
    name = "/stop"

    def run(self, app, arg: str) -> None:
        app.action_interrupt()
