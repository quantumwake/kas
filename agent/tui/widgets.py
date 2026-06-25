"""Small Textual widgets and modal screens for the TUI: the model picker, the
subagent transcript viewer, the paste-preserving input, and the selectable log.
All are self-contained — they talk to the app (when at all) by duck-typed
attribute access, never by importing AgentApp.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, RichLog, Static
from textual.widgets.option_list import Option


class ModelSelect(ModalScreen):
    """Arrow-key/click model picker (↑↓ + Enter, Esc to cancel)."""

    CSS = """
    ModelSelect { align: center middle; }
    #ms-box { width: 80%; max-width: 90; height: auto; max-height: 80%;
              background: #1a0e00; border: round #ff9d00; padding: 1 2; }
    #ms-title { color: #ffb000; text-style: bold; padding-bottom: 1; }
    ModelSelect OptionList { background: #1a0e00; color: #ffb000; border: none; }
    ModelSelect OptionList > .option-list--option-highlighted {
        background: #ff9d00; color: #1a0e00; text-style: bold; }
    """
    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def __init__(self, models: list[str], current: str) -> None:
        super().__init__()
        self._models = models
        self._current = current
        from scripts.select_model import model_info

        self._info = {m["id"]: m for m in model_info()}

    def _label(self, m: str) -> Text:
        meta = self._info.get(m, {})
        t = Text()
        t.append("● " if m == self._current else "  ", style="#3fb950")
        t.append(m)
        if meta:
            t.append(f"  {meta['size_h']}", style="#8a8a8a")
            if not meta["complete"]:
                t.append("  ⏳ partial", style="#ffa657")
        return t

    def compose(self) -> ComposeResult:
        with Vertical(id="ms-box"):
            yield Static("select a model  ·  ↑↓ + Enter  ·  Esc to cancel", id="ms-title")
            yield OptionList(*[Option(self._label(m), id=m) for m in self._models])

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SpecWizard(ModalScreen):
    """/spec step 1: pick what you're building (↑↓ + Enter, Esc to cancel).

    Returns the chosen project kind via dismiss(); the LLM follow-up questions
    and the spec itself happen in the normal chat afterward (see core.spec)."""

    CSS = """
    SpecWizard { align: center middle; }
    #sw-box { width: 70%; max-width: 70; height: auto; max-height: 80%;
              background: #1a0e00; border: round #ff9d00; padding: 1 2; }
    #sw-title { color: #ffb000; text-style: bold; padding-bottom: 1; }
    SpecWizard OptionList { background: #1a0e00; color: #ffb000; border: none; }
    SpecWizard OptionList > .option-list--option-highlighted {
        background: #ff9d00; color: #1a0e00; text-style: bold; }
    """
    BINDINGS = [Binding("escape", "cancel", "cancel")]

    def compose(self) -> ComposeResult:
        from agent.core.spec import PROJECT_KINDS

        with Vertical(id="sw-box"):
            yield Static("/spec — what are you building?  ·  ↑↓ + Enter  ·  Esc", id="sw-title")
            yield OptionList(*[Option(k, id=k) for k in PROJECT_KINDS])

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SubagentView(ModalScreen):
    """Scrollable read-only view of one subagent's captured transcript."""

    CSS = """
    SubagentView { align: center middle; }
    #sv-box { width: 90%; height: 85%; background: #0a0500; border: round #ff9d00; padding: 1 2; }
    #sv-title { color: #ffb000; text-style: bold; padding-bottom: 1; }
    SubagentView RichLog { background: #0a0500; color: #cc7000; }
    """
    BINDINGS = [Binding("escape", "dismiss", "close")]

    def __init__(self, sub) -> None:
        super().__init__()
        self._sub = sub

    def compose(self) -> ComposeResult:
        with Vertical(id="sv-box"):
            yield Static(
                f"subagent[{self._sub.n}] · {self._sub.status} · {self._sub.label}  (Esc to close)",
                id="sv-title",
            )
            log = RichLog(wrap=True, markup=False, highlight=False)
            yield log

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        for line in self._sub.buffer or ["(no captured output)"]:
            log.write(Text(line, style="#cc7000"))

    def action_dismiss(self) -> None:
        self.dismiss(None)


class PasteInput(Input):
    """Single-line Input that doesn't shred multiline paste.

    Stock Input._on_paste keeps only splitlines()[0]. We intercept a multiline
    paste and hand the full text to the app to stage (attached to the next
    message) instead of flattening it into the one-line field.
    """

    def _on_paste(self, event) -> None:
        if event.text and "\n" in event.text:
            self.app.stage_paste(event.text)
            event.stop()
            return
        super()._on_paste(event)

    def on_key(self, event) -> None:
        # During a command-confirmation, a single y / n / a answers it (no Enter)
        # and is NOT typed into the field. Handled here (the focused widget) so it
        # beats the Input's own character insertion; otherwise keys are normal.
        ch = (event.character or "").lower()
        if getattr(self.app, "confirming", False) and ch in ("y", "n", "a"):
            event.stop()
            event.prevent_default()
            self.app.action_confirm(ch)


class SelectableRichLog(RichLog):
    """RichLog with mouse text selection.

    Textual's selection machinery needs the widget to map a Selection to
    text; stock RichLog doesn't implement it. Its internal `lines` are the
    rendered visual lines (Strips), which is exactly the coordinate space
    selections are made in.
    """

    ALLOW_SELECT = True

    def get_selection(self, selection) -> tuple[str, str] | None:
        text = "\n".join(strip.text for strip in self.lines)
        return selection.extract(text), "\n"
