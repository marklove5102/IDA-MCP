"""Nuitka build script for the IDE."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _bootstrap_project_root() -> None:
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


_bootstrap_project_root()

from shared.paths import (
    ensure_directory,
    get_assets_root,
    get_nuitka_output_root,
    get_project_root,
    get_repo_root,
)


def build_command(*, onefile: bool = False) -> list[str]:
    project_root = get_project_root()
    launcher = project_root / "launcher.py"
    output_dir = ensure_directory(get_nuitka_output_root())
    assets_root = get_assets_root()
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile" if onefile else "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--msvc=latest",
        "--windows-console-mode=disable",
        "--include-package=app",
        "--include-package=shared",
        "--include-package=supervisor",
        f"--output-filename={launcher.stem}",
        f"--output-dir={output_dir}",
    ]

    if assets_root.exists() and any(assets_root.iterdir()):
        command.append(f"--include-data-dir={assets_root}=app/assets")

    requirements_path = get_repo_root() / "requirements.txt"
    if requirements_path.exists():
        command.append(
            f"--include-data-file={requirements_path}=app/assets/ida_mcp_requirements.txt"
        )

    icon_path = assets_root / "app.ico"
    if icon_path.exists():
        command.append(f"--windows-icon-from-ico={icon_path}")

    command.append(str(launcher))
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build IDE with Nuitka")
    parser.add_argument(
        "--mode",
        choices=("standalone", "onefile"),
        default="standalone",
        help="Nuitka packaging mode. Start with standalone before onefile.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the resolved Nuitka command without executing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = build_command(onefile=args.mode == "onefile")
    print("Running:", " ".join(command))
    if args.print_only:
        return 0
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
