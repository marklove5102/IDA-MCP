"""Platform adaptation layer.

Centralizes platform-specific differences so the rest of the codebase
does not scatter ``os.name`` checks across every module.  Initialized
once at import time.

Two domains are covered:

* **Display paths** — ensuring paths use the OS-native separator for
  human-readable output (CLI text, log messages, UI labels).
  Windows uses ``\\``, macOS / Linux use ``/``.
  This is *never* applied to machine-readable API payloads.
* **Platform queries** — cheap ``is_windows``, ``is_linux`` booleans and
  helpers that branch on the current OS without repeating ``os.name``
  checks everywhere.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Union

# ---------------------------------------------------------------------------
# Platform detection — resolved once at import time
# ---------------------------------------------------------------------------

IS_WINDOWS: bool = os.name == "nt"
"""True on Windows (including MSYS / Cygwin Python)."""

IS_LINUX: bool = sys.platform == "linux"
"""True on CPython/Linux.  Also True under WSL."""

IS_MACOS: bool = sys.platform == "darwin"
"""True on macOS."""

PATH_SEP: str = os.sep
"""The separator used by :func:`display_path` for display output.

``\\`` on Windows, ``/`` on POSIX — always the OS-native separator.
"""

# ---------------------------------------------------------------------------
# Display-path helper
# ---------------------------------------------------------------------------

_PathType = Union[str, Path, None]


def display_path(path: _PathType) -> str:
    """Return a path string using the OS-native separator for display.

    On Windows, forward slashes are replaced with backslashes (``\\``).
    On macOS / Linux, the path is returned as-is (already ``/``).
    ``None`` and empty strings return ``""``.

    This function is **only** for human-facing output (CLI text, log
    lines, UI labels).  Do *not* use it in machine-readable API payloads
    or return structs consumed by other tools or tests.
    """
    if path is None:
        return ""
    text = str(path)
    if IS_WINDOWS and "/" in text:
        text = text.replace("/", "\\")
    return text


def display_path_or_none(path: _PathType) -> Optional[str]:
    """Like :func:`display_path` but returns ``None`` when *path* is falsy."""
    if not path:
        return None
    return display_path(path)


# ---------------------------------------------------------------------------
# Platform-specific path helpers
# ---------------------------------------------------------------------------

def is_same_path(a: _PathType, b: _PathType) -> bool:
    """Compare two paths in a platform-aware way.

    On Windows the comparison is case-insensitive after normalizing
    separators; on POSIX it is case-sensitive.
    """
    sa = display_path(a)
    sb = display_path(b)
    if IS_WINDOWS:
        return sa.lower() == sb.lower()
    return sa == sb
