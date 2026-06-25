"""/spec — a guided spec wizard.

Hybrid: a TUI selection screen picks the project KIND, then this seeds a normal
agent turn with SPEC MODE instructions. The ordinary loop does the rest — asks a
few LLM-inferred clarifying questions, writes SPEC.md (goal · requirements ·
checklist · plan), waits for approval, then builds through the checklist. No
special loop wiring: spec mode is just a prompt prepended to the seed message, so
the agent reads it as instructions and the transcript stays a normal conversation.
"""

# Offered in the wizard's selection screen.
PROJECT_KINDS = [
    "game",
    "web app",
    "backend service / API",
    "CLI tool",
    "library / package",
    "data / ML pipeline",
    "automation / script",
    "other",
]

SPEC_PROMPT = (
    "You are in SPEC MODE — a short, focused requirements wizard. The user is "
    "building: {kind}. Proceed in order, and do NOT skip ahead:\n"
    "1) Ask 3–5 SHARP clarifying questions in ONE concise message — cover the "
    "stack/language, the key features, hard constraints, and the success / 'done' "
    "criteria. Don't over-ask or pad. Then wait for the answers.\n"
    "2) Once you have enough, WRITE `SPEC.md` in the working directory with these "
    "sections: `## Goal` (1–2 sentences) · `## Requirements` · `## Checklist` "
    "(markdown `- [ ]` items, ordered, each small and independently buildable) · "
    "`## Plan` (the build order). Keep it tight and concrete — no fluff.\n"
    "3) Then STOP and ask the user to review SPEC.md and reply 'go' to build (or "
    "request changes). Do NOT start building before they approve.\n"
    "4) After approval, work through the checklist end to end, checking items off "
    "in SPEC.md as you finish them (edit `- [ ]` → `- [x]`), and only present the "
    "final result once every item is done."
)


def spec_seed(kind: str) -> str:
    """The first user message that puts the agent into spec mode for `kind`."""
    kind = (kind or "other").strip() or "other"
    return f"{SPEC_PROMPT.format(kind=kind)}\n\nI'm building: {kind}. Let's spec it out."
