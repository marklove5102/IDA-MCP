"""Shared path helpers for development and packaged IDE runtimes."""

from __future__ import annotations

import os
from pathlib import Path

from shared.runtime import get_packaging_root as get_runtime_packaging_root
from shared.runtime import get_runtime_root


def get_project_root() -> Path:
    """Return the IDE project root for both dev and packaged modes."""
    return get_runtime_root()


def get_resources_root() -> Path:
    """Return the bundled resources directory (contains ida_mcp source, etc.)."""
    return get_project_root() / "resources"


def get_ida_mcp_resources_dir() -> Path:
    """Return the ida_mcp bundled resource directory."""
    return get_resources_root() / "ida_mcp"


def get_logs_root() -> Path:
    """Return the logs directory for the current runtime mode."""
    return get_project_root() / "logs"


def get_workspaces_root() -> Path:
    """Return the workspaces directory for the current runtime mode."""
    return get_project_root() / "workspaces"


def get_build_root() -> Path:
    """Return the local build root used by developer tooling."""
    return get_project_root() / "build"


def get_nuitka_output_root() -> Path:
    """Return the base output root used by Nuitka builds."""
    return get_build_root() / "nuitka"


def get_packaging_root() -> Path:
    """Return the packaging helpers root for the current runtime mode."""
    return get_runtime_packaging_root()


def get_user_config_root(app_name: str = "ida-mcp") -> Path:
    """Return a per-user config directory without writing into the repo."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / app_name
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / app_name
    return Path.home() / ".config" / app_name


def get_ide_user_config_root(app_name: str = "ida-mcp") -> Path:
    """Return the IDE-specific config root below the application config root."""
    return get_user_config_root(app_name) / "ide"


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
