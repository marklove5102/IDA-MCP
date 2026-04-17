"""Minimal CLI entrypoint for the supervisor MVP."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .manager import SupervisorManager


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ide.supervisor.main")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show supervisor snapshot")
    subparsers.add_parser("probe", help="Show environment probe")
    subparsers.add_parser("start-gateway", help="Start the gateway")

    stop_parser = subparsers.add_parser("stop-gateway", help="Stop the gateway")
    stop_parser.add_argument("--force", action="store_true")

    config_parser = subparsers.add_parser("set-config", help="Update stored config")
    config_parser.add_argument("--plugin-dir")
    config_parser.add_argument("--ida-path")
    config_parser.add_argument("--ida-python")
    config_parser.add_argument("--auto-start-gateway", choices=["true", "false"])
    config_parser.add_argument("--request-timeout", type=int)
    config_parser.add_argument("--notes")
    return parser


def _print_payload(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manager = SupervisorManager()

    if args.command == "status":
        _print_payload(manager.get_snapshot())
        return 0
    if args.command == "probe":
        _print_payload(manager.probe_environment())
        return 0
    if args.command == "start-gateway":
        _print_payload(manager.start_gateway())
        return 0
    if args.command == "stop-gateway":
        _print_payload(manager.stop_gateway(force=bool(args.force)))
        return 0
    if args.command == "set-config":
        ide_updates: dict[str, Any] = {
            "plugin_dir": args.plugin_dir,
            "request_timeout": args.request_timeout,
            "notes": args.notes,
        }
        if args.auto_start_gateway is not None:
            ide_updates["auto_start_gateway"] = args.auto_start_gateway == "true"

        ida_mcp_updates: dict[str, Any] = {}
        if args.ida_path is not None:
            ida_mcp_updates["ida_path"] = args.ida_path
        if args.ida_python is not None:
            ida_mcp_updates["ida_python"] = args.ida_python

        if ida_mcp_updates:
            manager.update_ida_mcp_config(**ida_mcp_updates)
        _print_payload(manager.update_config(**ide_updates))
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
