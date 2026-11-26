"""Code version recorded in every report (docs/SCOPE.md NF-3)."""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

__version__ = "0.1.0"


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    return out.stdout.strip()


@lru_cache(maxsize=1)
def code_version() -> str:
    """'0.1.0 (a1b2c3d)' from a git checkout, '0.1.0 (a1b2c3d-dirty)' with uncommitted changes, else '0.1.0'."""
    try:
        sha = _git("rev-parse", "--short", "HEAD")
        dirty = _git("status", "--porcelain", "--untracked-files=no")
    except (OSError, subprocess.SubprocessError):
        return __version__
    return f"{__version__} ({sha}{'-dirty' if dirty else ''})"
