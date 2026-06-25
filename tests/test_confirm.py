"""Headless test for the single-key command-confirmation UI: while NOT confirming,
y/n/a type into the input normally; during a confirmation a single y/n/a keypress
resolves it (no Enter) and is not typed. Mounts AgentApp via Textual run_test at a
dead port (no server). No model needed.

Run:  uv run python tests/test_confirm.py
"""

import asyncio
import pathlib
import sys
import tempfile

sys.path.insert(0, ".")

import anthropic

from agent.tui import AgentApp


async def _check() -> None:
    app = AgentApp(
        client=anthropic.Anthropic(base_url="http://127.0.0.1:9", api_key="x", max_retries=0),
        model="m",
        base_url="http://127.0.0.1:9",
        workdir=pathlib.Path(tempfile.mkdtemp()),
        yolo=False,
    )
    async with app.run_test(size=(90, 30)) as pilot:
        await pilot.pause(0.2)
        inp = app.query_one("#input")

        # not confirming: y/n/a type normally
        await pilot.press("y", "e", "s")
        await pilot.pause(0.05)
        assert inp.value == "yes", f"normal typing broken: {inp.value!r}"
        inp.value = ""

        # confirming: a single key answers it and is NOT typed
        app.enter_confirm("rm -rf build/")
        await pilot.pause(0.05)
        assert app.confirming is True
        await pilot.press("a")
        await pilot.pause(0.05)
        assert app.confirming is False, "still confirming after keypress"
        assert app.io.confirm_q.get_nowait() == "a", "answer not queued"
        assert inp.value == "", f"key leaked into input: {inp.value!r}"

        # a fresh confirmation resolves with a different key
        app.enter_confirm("ls")
        await pilot.pause(0.05)
        await pilot.press("n")
        await pilot.pause(0.05)
        assert app.io.confirm_q.get_nowait() == "n"


asyncio.run(_check())
print("confirm UI: normal typing + single-key y/n/a resolution OK")
print("all confirm tests passed")
