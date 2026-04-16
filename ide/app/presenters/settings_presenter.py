"""Presentation helpers for the settings page."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.services.settings_service import SettingsSnapshot
from supervisor.models import HealthReport, InstallationActionResult, InstallationCheck


@dataclass(slots=True)
class SettingsFormState:
    python_path: str
    plugin_dir: str
    language: str
    ide_request_timeout: int
    enable_http: bool
    enable_stdio: bool
    enable_unsafe: bool
    wsl_path_bridge: bool
    http_host: str
    http_port: int
    http_path: str
    ida_default_port: int
    ida_host: str
    ida_path: str
    ida_python: str
    open_in_ida_bundle_dir: str
    open_in_ida_autonomous: bool
    auto_start: bool
    server_name: str
    ida_request_timeout: int
    debug: bool


@dataclass(slots=True)
class SettingsMessage:
    summary: str
    details: str


def snapshot_to_form_state(snapshot: SettingsSnapshot) -> SettingsFormState:
    ide_config = snapshot.ide_config
    ida_mcp_config = snapshot.ida_mcp_config
    return SettingsFormState(
        python_path=ide_config.python_path or "",
        plugin_dir=ide_config.plugin_dir or "",
        language=ide_config.language,
        ide_request_timeout=ide_config.request_timeout,
        enable_http=ida_mcp_config.enable_http,
        enable_stdio=ida_mcp_config.enable_stdio,
        enable_unsafe=ida_mcp_config.enable_unsafe,
        wsl_path_bridge=ida_mcp_config.wsl_path_bridge,
        http_host=ida_mcp_config.http_host,
        http_port=ida_mcp_config.http_port,
        http_path=ida_mcp_config.http_path,
        ida_default_port=ida_mcp_config.ida_default_port,
        ida_host=ida_mcp_config.ida_host,
        ida_path=ida_mcp_config.ida_path or "",
        ida_python=ida_mcp_config.ida_python or "",
        open_in_ida_bundle_dir=ida_mcp_config.open_in_ida_bundle_dir or "",
        open_in_ida_autonomous=ida_mcp_config.open_in_ida_autonomous,
        auto_start=ida_mcp_config.auto_start,
        server_name=ida_mcp_config.server_name,
        ida_request_timeout=ida_mcp_config.request_timeout,
        debug=ida_mcp_config.debug,
    )


def effective_install_python_path(snapshot: SettingsSnapshot) -> str:
    return snapshot.ide_config.python_path or snapshot.ida_mcp_config.ida_python or ""


def form_state_to_updates(
    state: SettingsFormState,
) -> tuple[dict[str, object], dict[str, object]]:
    return (
        {
            "python_path": _clean_optional(state.python_path),
            "plugin_dir": _clean_optional(state.plugin_dir),
            "request_timeout": state.ide_request_timeout,
            "language": state.language,
        },
        {
            "enable_http": state.enable_http,
            "enable_stdio": state.enable_stdio,
            "enable_unsafe": state.enable_unsafe,
            "wsl_path_bridge": state.wsl_path_bridge,
            "http_host": state.http_host.strip() or "0.0.0.0",
            "http_port": state.http_port,
            "http_path": state.http_path.strip() or "/mcp",
            "ida_default_port": state.ida_default_port,
            "ida_host": state.ida_host.strip() or "127.0.0.1",
            "ida_path": _clean_optional(state.ida_path),
            "ida_python": _clean_optional(state.ida_python),
            "open_in_ida_bundle_dir": _clean_optional(state.open_in_ida_bundle_dir),
            "open_in_ida_autonomous": state.open_in_ida_autonomous,
            "auto_start": state.auto_start,
            "server_name": state.server_name.strip() or "IDA-MCP",
            "request_timeout": state.ida_request_timeout,
            "debug": state.debug,
        },
    )


def build_check_message(
    report: HealthReport,
    installation: InstallationCheck,
    translate: Callable[[str], str],
    bool_text: Callable[[bool], str],
) -> SettingsMessage:
    lines = [
        f"Supervisor: {report.supervisor.state.value} - {report.supervisor.summary}",
        f"Gateway: {report.gateway.state.value} - {report.gateway.summary}",
        f"Environment: {report.environment.state.value} - {report.environment.summary}",
        "",
        f"{translate('settings.install.status')}:",
        f"- {translate('settings.install.plugin_dir')}: {installation.plugin_dir or '(not found)'}",
        f"- {translate('settings.install.config')}: {installation.config_path or '(not resolved)'} [{bool_text(installation.config_exists)}]",
        f"- {translate('settings.install.python')}: {installation.python_executable or '(not found)'} [{bool_text(installation.python_exists)}]",
        f"- {translate('settings.install.ida_mcp_py')}: {bool_text(installation.ida_mcp_py_exists)}",
        f"- {translate('settings.install.ida_mcp_pkg')}: {bool_text(installation.ida_mcp_package_exists)}",
        "",
        f"{translate('settings.install.requirements')}:",
        f"- {translate('settings.install.requirements_path')}: {installation.requirements_path or '(not found)'}",
        f"- {translate('settings.install.requirements_status')}: {_format_requirement_summary(installation)}",
    ]
    if installation.warnings:
        lines.extend(
            ["", translate("settings.install.warning")]
            + [f"- {item}" for item in installation.warnings]
        )
    return SettingsMessage(summary=installation.summary, details="\n".join(lines))


def build_reinstall_message(
    result: InstallationActionResult,
    translate: Callable[[str], str],
    bool_text: Callable[[bool], str],
) -> SettingsMessage:
    lines = [
        result.summary,
        "",
        f"{translate('settings.install.plugin_dir')}: {result.check.plugin_dir or '(not found)'}",
        f"{translate('settings.install.config')}: {result.config_path or result.check.config_path or '(not resolved)'}",
        f"{translate('settings.install.created')}: {bool_text(result.created)}",
        f"{translate('settings.install.already_exists')}: {bool_text(result.already_exists)}",
        f"{translate('settings.install.python_exists')}: {bool_text(result.check.python_exists)}",
        f"{translate('settings.install.requirements_status')}: {_format_requirement_summary(result.check)}",
    ]
    if result.warnings:
        lines.extend(
            ["", translate("settings.install.warning")]
            + [f"- {item}" for item in result.warnings]
        )
    return SettingsMessage(summary=result.summary, details="\n".join(lines))


def _clean_optional(value: str) -> str | None:
    cleaned = value.strip()
    return cleaned or None


def _format_requirement_summary(installation: InstallationCheck) -> str:
    total = len(installation.requirements)
    installed = len(installation.installed_requirements)
    missing = len(installation.missing_requirements)
    unresolved = len(installation.unresolved_requirements)
    parts = [f"{installed}/{total} installed"]
    if missing:
        parts.append(f"{missing} missing")
    if unresolved:
        parts.append(f"{unresolved} unresolved")
    return ", ".join(parts)
