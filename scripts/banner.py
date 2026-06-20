"""K.A.S — BBS-style amber-on-black startup banner.

Shared by the server, the console REPL, and the TUI. Old-school terminal
flavor: ANSI Shadow block letters, box-drawing border, amber/orange text.
"""

import sys
import time

TAGLINE = "agentic coding shell"
SUBTAG = "local agents on your own iron"
EST = "est. 2026"

# ANSI Shadow figlet — "KASCODE" (each glyph padded to 8 cols so they align)
ART = [
    "██╗  ██╗ █████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗",
    "██║ ██╔╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝",
    "█████╔╝ ███████║███████╗██║     ██║  ██║██║  ██║█████╗  ",
    "██╔═██╗ ██╔══██║╚════██║██║     ██║  ██║██║  ██║██╔══╝  ",
    "██║  ██╗██║  ██║███████║╚██████╗╚█████╔╝██████╔╝███████╗",
    "╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚════╝ ╚═════╝ ╚══════╝",
]

# 256-color amber/orange on black
AMBER = "\033[38;5;214m"
ORANGE = "\033[38;5;208m"
DIM_AMBER = "\033[38;5;130m"
BLACK_BG = "\033[40m"
BOLD = "\033[1m"
RST = "\033[0m"

# Warm vertical gradient down the 6 block-letter rows — a soft CRT glow (bright
# gold at the top fading to deep orange) instead of one flat colour.
ART_RAMP = [222, 220, 214, 208, 202, 166]
ART_RAMP_HEX = ["#ffdf91", "#ffd152", "#ffb000", "#ff9d00", "#ff7a00", "#e05a10"]

_WIDTH = 64


def _box_lines(model: str | None, extra: str | None) -> list[tuple[str, str]]:
    """Return (text, role) lines; role in {art, title, sub, info, rule}."""
    inner = _WIDTH - 2
    rows: list[tuple[str, str]] = []
    rows.append(("╔" + "═" * inner + "╗", "rule"))
    for a in ART:
        pad = inner - len(a) - 3
        rows.append(("║  " + a + " " * max(0, pad) + " ║", "art"))
    rows.append(("║" + " " * inner + "║", "rule"))
    title = f"kascode  ·  {TAGLINE}"
    rows.append(("║  " + title.ljust(inner - 3) + " ║", "title"))
    rows.append(("║  " + f"{SUBTAG}  ·  {EST}".ljust(inner - 3) + " ║", "sub"))
    if model:
        rows.append(("║  " + f"model : {model}".ljust(inner - 3)[: inner - 3] + " ║", "info"))
    if extra:
        rows.append(("║  " + extra.ljust(inner - 3)[: inner - 3] + " ║", "info"))
    rows.append(("╚" + "═" * inner + "╝", "rule"))
    return rows


def set_title(text: str = "kascode · agentic coding shell") -> None:
    if sys.stdout.isatty():
        sys.stdout.write(f"\033]0;{text}\007")
        sys.stdout.flush()


def print_console(model: str | None = None, extra: str | None = None, animate: bool = True) -> None:
    """Print the amber/black banner to the terminal (server + console REPL)."""
    set_title()
    color = {"title": AMBER + BOLD, "sub": DIM_AMBER, "info": AMBER, "rule": DIM_AMBER}
    out = []
    art_i = 0
    for text, role in _box_lines(model, extra):
        if role == "art":
            shade = ART_RAMP[art_i % len(ART_RAMP)]
            out.append(f"{BOLD}\033[38;5;{shade}m{text}{RST}")
            art_i += 1
        else:
            out.append(f"{color[role]}{text}{RST}")
    # Cascade-reveal the lines top→bottom for a little startup flourish — but
    # only on a real terminal (a logged/piped run prints it all at once).
    animate = animate and sys.stdout.isatty()
    for line in out:
        print(line, flush=True)
        if animate:
            time.sleep(0.035)
    print()


def tui_lines(model: str | None = None, extra: str | None = None):
    """Return [(text, style)] for rendering in the Textual work view."""
    style = {"title": "bold #ffb000", "sub": "#cc7000", "info": "#ffb000", "rule": "#aa5d00"}
    out, art_i = [], 0
    for text, role in _box_lines(model, extra):
        if role == "art":
            out.append((text, f"bold {ART_RAMP_HEX[art_i % len(ART_RAMP_HEX)]}"))
            art_i += 1
        else:
            out.append((text, style[role]))
    return out
