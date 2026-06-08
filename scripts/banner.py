"""K.A.S — BBS-style amber-on-black startup banner.

Shared by the server, the console REPL, and the TUI. Old-school terminal
flavor: ANSI Shadow block letters, box-drawing border, amber/orange text.
"""

import sys

TAGLINE = "Kasra's Agentic Shell"
SUBTAG = "local agents on your own iron"
EST = "EST 2026"

# ANSI Shadow figlet — "KAS"
ART = [
    "██╗  ██╗  █████╗  ███████╗",
    "██║ ██╔╝ ██╔══██╗ ██╔════╝",
    "█████╔╝  ███████║ ███████╗",
    "██╔═██╗  ██╔══██║ ╚════██║",
    "██║  ██╗ ██║  ██║ ███████║",
    "╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚══════╝",
]

# 256-color amber/orange on black
AMBER = "\033[38;5;214m"
ORANGE = "\033[38;5;208m"
DIM_AMBER = "\033[38;5;130m"
BLACK_BG = "\033[40m"
BOLD = "\033[1m"
RST = "\033[0m"

_WIDTH = 60


def _box_lines(model: str | None, extra: str | None) -> list[tuple[str, str]]:
    """Return (text, role) lines; role in {art, title, sub, info, rule}."""
    inner = _WIDTH - 2
    rows: list[tuple[str, str]] = []
    rows.append(("╔" + "═" * inner + "╗", "rule"))
    for a in ART:
        pad = inner - len(a) - 3
        rows.append(("║  " + a + " " * max(0, pad) + " ║", "art"))
    rows.append(("║" + " " * inner + "║", "rule"))
    title = f"K.A.S  ·  {TAGLINE}"
    rows.append(("║  " + title.ljust(inner - 3) + " ║", "title"))
    rows.append(("║  " + f"{SUBTAG}  ·  {EST}".ljust(inner - 3) + " ║", "sub"))
    if model:
        rows.append(("║  " + f"model : {model}".ljust(inner - 3)[: inner - 3] + " ║", "info"))
    if extra:
        rows.append(("║  " + extra.ljust(inner - 3)[: inner - 3] + " ║", "info"))
    rows.append(("╚" + "═" * inner + "╝", "rule"))
    return rows


def set_title(text: str = "K.A.S · Kasra's Agentic Shell") -> None:
    if sys.stdout.isatty():
        sys.stdout.write(f"\033]0;{text}\007")
        sys.stdout.flush()


def print_console(model: str | None = None, extra: str | None = None) -> None:
    """Print the amber/black banner to the terminal (server + console REPL)."""
    set_title()
    color = {"art": ORANGE + BOLD, "title": AMBER + BOLD, "sub": DIM_AMBER,
             "info": AMBER, "rule": DIM_AMBER}
    out = []
    for text, role in _box_lines(model, extra):
        out.append(f"{color[role]}{text}{RST}")
    print("\n".join(out))
    print()


def tui_lines(model: str | None = None, extra: str | None = None):
    """Return [(text, style)] for rendering in the Textual work view."""
    style = {"art": "bold #ff8c00", "title": "bold #ffb000", "sub": "#cc7000",
             "info": "#ffb000", "rule": "#aa5d00"}
    return [(text, style[role]) for text, role in _box_lines(model, extra)]
