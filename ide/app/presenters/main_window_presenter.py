"""Presentation helpers for the main window."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Callable

from shared.platform import display_path as _display_path
from supervisor.models import ComponentHealth, SupervisorSnapshot


STATUS_CARD_TITLE_KEYS = {
    "supervisor": "main.status.card.supervisor",
    "gateway": "main.status.card.gateway",
    "environment": "main.status.card.environment",
    "instances": "main.status.card.instances",
}


FIELD_LABEL_KEYS = {
    "gateway_state": "main.field.gateway_state",
    "gateway_alive": "main.field.gateway_alive",
    "instance_count": "main.field.instance_count",
    "gateway_host": "main.field.gateway_host",
    "gateway_port": "main.field.gateway_port",
    "ide_config": "main.field.ide_config",
    "plugin_dir": "main.field.plugin_dir",
    "request_timeout": "main.field.request_timeout",
    "status": "main.field.status",
    "current_step": "main.field.current_step",
    "notes": "main.field.notes",
    "config": "main.field.config",
    "auto_start_gateway": "main.field.auto_start_gateway",
    "state": "main.field.state",
    "alive": "main.field.alive",
    "host": "main.field.host",
    "port": "main.field.port",
    "path": "main.field.path",
    "instances": "main.field.instances",
    "python": "main.field.python",
    "ida_mcp": "main.field.ida_mcp",
    "ida_paths": "main.field.ida_paths",
    "warnings": "main.field.warnings",
}


@dataclass(slots=True)
class TreeRowViewModel:
    label: str
    value: str


@dataclass(slots=True)
class StatusCardViewModel:
    key: str
    title: str
    state_text: str
    state_property: str
    summary: str
    details: str


@dataclass(slots=True)
class MainWindowViewModel:
    status_cards: list[StatusCardViewModel]
    ida_rows: list[TreeRowViewModel]
    workspace_rows: list[TreeRowViewModel]
    plan_rows: list[TreeRowViewModel]


def build_main_window_view_model(
    snapshot: SupervisorSnapshot,
    translate: Callable[[str], str],
) -> MainWindowViewModel:
    return MainWindowViewModel(
        status_cards=[
            _build_status_card_view_model(
                "supervisor",
                snapshot.health.supervisor,
                {
                    "config": _display_path(snapshot.config_store.path),
                    "auto_start_gateway": snapshot.config.auto_start_gateway,
                    "request_timeout": snapshot.config.request_timeout,
                    "plugin_dir": _display_path(snapshot.config.plugin_dir or ""),
                },
                translate,
            ),
            _build_status_card_view_model(
                "gateway",
                snapshot.health.gateway,
                {
                    "state": snapshot.gateway.state,
                    "alive": snapshot.gateway.alive,
                    "host": snapshot.gateway.host,
                    "port": snapshot.gateway.port,
                    "path": snapshot.gateway.path,
                    "instances": snapshot.gateway.instance_count,
                },
                translate,
            ),
            _build_status_card_view_model(
                "environment",
                snapshot.health.environment,
                {
                    "python": _display_path(snapshot.environment.python_executable or ""),
                    "ida_mcp": _display_path(snapshot.environment.ida_mcp_location or ""),
                    "ida_paths": [_display_path(p) for p in (snapshot.environment.ida_path_candidates or [])],
                    "warnings": snapshot.environment.warnings,
                },
                translate,
            ),
            _build_instances_card_view_model(snapshot, translate),
        ],
        ida_rows=_build_tree_rows(
            {
                "gateway_state": snapshot.gateway.state,
                "gateway_alive": snapshot.gateway.alive,
                "instance_count": snapshot.gateway.instance_count,
                "gateway_host": snapshot.gateway.host,
                "gateway_port": snapshot.gateway.port,
            },
            translate,
        ),
        workspace_rows=_build_tree_rows(
            {
                "ide_config": _display_path(snapshot.config_store.path),
                "plugin_dir": _display_path(snapshot.config.plugin_dir or ""),
                "request_timeout": snapshot.config.request_timeout,
            },
            translate,
        ),
        plan_rows=_build_tree_rows(
            {
                "status": translate("main.value.not_started"),
                "current_step": translate("main.value.pending"),
                "notes": snapshot.config.notes or "",
            },
            translate,
        ),
    )


def _build_tree_rows(
    mapping: dict[str, Any], translate: Callable[[str], str]
) -> list[TreeRowViewModel]:
    return [
        TreeRowViewModel(_field_label(key, translate), _display_value(value, translate))
        for key, value in mapping.items()
    ]


def _build_instances_card_view_model(
    snapshot: SupervisorSnapshot,
    translate: Callable[[str], str],
) -> StatusCardViewModel:
    instances = snapshot.gateway.instances
    count = len(instances)
    if count == 0:
        return StatusCardViewModel(
            key="instances",
            title=translate(STATUS_CARD_TITLE_KEYS["instances"]),
            state_text=translate(
                "main.status.label.state", state=translate("common.state.unknown")
            ),
            state_property="unknown",
            summary=translate("main.status.instances.empty"),
            details="",
        )

    lines: list[str] = []
    for i, inst in enumerate(instances, 1):
        pid = inst.get("pid", "?")
        port = inst.get("port", "?")
        state = inst.get("effective_state", inst.get("health", "?"))
        input_file = inst.get("input_file", "")
        idb = inst.get("idb", "")
        file_name = ""
        if input_file:
            from pathlib import PurePath

            file_name = PurePath(_display_path(input_file)).name
        elif idb:
            from pathlib import PurePath

            file_name = PurePath(_display_path(idb)).name
        label = f"#{i}  :{port}  {state}"
        if file_name:
            label += f"  {file_name}"
        lines.append(label)

    return StatusCardViewModel(
        key="instances",
        title=translate(STATUS_CARD_TITLE_KEYS["instances"]),
        state_text=translate("main.status.label.state", state=f"{count}"),
        state_property="ok" if count > 0 else "unknown",
        summary=translate("main.status.instances.count", count=count),
        details="\n".join(lines),
    )


def _build_status_card_view_model(
    key: str,
    health: ComponentHealth,
    details: dict[str, Any],
    translate: Callable[[str], str],
) -> StatusCardViewModel:
    return StatusCardViewModel(
        key=key,
        title=translate(STATUS_CARD_TITLE_KEYS[key]),
        state_text=translate(
            "main.status.label.state", state=_display_value(health.state, translate)
        ),
        state_property=health.state.value,
        summary=health.summary,
        details="\n".join(
            f"{_field_label(name, translate)}: {_display_or_placeholder(value, translate)}"
            for name, value in details.items()
        ),
    )


def _display_or_placeholder(value: Any, translate: Callable[[str], str]) -> str:
    text = _display_value(value, translate)
    return text if text.strip() else "-"


def _display_value(value: Any, translate: Callable[[str], str]) -> str:
    if isinstance(value, Enum):
        return translate(f"common.state.{value.value}")
    if isinstance(value, bool):
        return translate("common.bool.true" if value else "common.bool.false")
    if is_dataclass(value):
        return _display_value(asdict(value), translate)
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            nested = _display_value(item, translate)
            if "\n" in nested:
                nested = "\n".join(f"  {line}" for line in nested.splitlines())
            lines.append(f"{_field_label(str(key), translate)}: {nested}")
        return "\n".join(lines)
    if isinstance(value, list):
        return (
            "\n".join(f"- {_display_value(item, translate)}" for item in value) or "[]"
        )
    return str(value)


def _field_label(key: str, translate: Callable[[str], str]) -> str:
    return translate(FIELD_LABEL_KEYS.get(key, key))
