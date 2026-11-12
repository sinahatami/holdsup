"""Running an exported notebook as a reader would: every code cell in order, in one namespace."""

import subprocess
import sys
from pathlib import Path
from typing import Any

from holdsup.receipt.notebook import Notebook, code_cells


def execute(nb: Notebook) -> dict[str, Any]:  # Any: the notebook's own variables
    """Run every code cell in this process; returns the cells' namespace."""
    namespace: dict[str, Any] = {"__name__": "__main__"}
    for source in code_cells(nb):
        exec(compile(source, "<notebook cell>", "exec"), namespace)  # noqa: S102 - our own export
    return namespace


def execute_standalone(nb: Notebook, folder: Path) -> str:
    """Run every code cell in a fresh Python with no site-packages (`-I -S`): only the standard
    library, so the notebook cannot lean on HoldsUp or anything installed beside it. Returns
    what it printed; a failing cell fails the run."""
    script = folder / "notebook.py"
    script.write_text("\n\n".join(code_cells(nb)), encoding="utf-8")
    done = subprocess.run(  # noqa: S603 - our interpreter, our script
        [sys.executable, "-I", "-S", str(script)],
        cwd=folder,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout
