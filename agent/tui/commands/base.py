"""Base class for TUI slash commands.

Each command is a small class in its own module in this package; the registry in
__init__ dispatches submitted /lines to them. Adding a command = a new module + a
line in REGISTRY — no edits to a central dispatcher.
"""


class Command:
    name: str = ""  # the primary "/name"

    def match(self, text: str) -> str | None:
        """Return the raw argument remainder (the text after `name`) if this
        command handles `text`, else None. Default: an exact `/name`, or
        `/name <arg>`. Prefix-style commands (e.g. /model) override this."""
        if text == self.name or text.startswith(self.name + " "):
            return text[len(self.name) :]
        return None

    def run(self, app, arg: str) -> None:
        """Execute against the AgentApp `app`. `arg` is the raw remainder; the
        command normalises it (strip/lower) as needed."""
        raise NotImplementedError
