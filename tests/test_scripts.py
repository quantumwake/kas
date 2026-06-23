"""Pytest collector for the standalone characterization scripts.

The other tests in this directory run as `python tests/test_x.py` with bare
module-level asserts. Rather than rewrite them, this shim runs each in-process
via runpy so pytest collects them and `pytest-cov` can measure product coverage.
A failing assert in a script surfaces as a failed parametrized test here.

`python_files = ["test_scripts.py"]` (pyproject) keeps pytest from importing the
scripts directly — only this file is collected; it drives the rest.
"""

import pathlib
import runpy
import sys

import pytest

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
SCRIPTS = sorted(p.name for p in HERE.glob("test_*.py") if p.name != "test_scripts.py")


@pytest.mark.parametrize("script", SCRIPTS)
def test_characterization_script(script: str) -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    runpy.run_path(str(HERE / script), run_name="__main__")
