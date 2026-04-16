"""Settings service for IDE MVP."""

from __future__ import annotations

from dataclasses import dataclass

from app.i18n import normalize_language
from app.services.supervisor_client import SupervisorClient
from supervisor.models import (
    HealthReport,
    IdaMcpConfig,
    InstallationActionResult,
    InstallationCheck,
    IdeConfig,
)


@dataclass(slots=True)
class SettingsSnapshot:
    ide_config: IdeConfig
    ida_mcp_config: IdaMcpConfig


class SettingsService:
    def __init__(self, supervisor_client: SupervisorClient | None = None) -> None:
        self._supervisor_client = supervisor_client or SupervisorClient()

    def load(self) -> SettingsSnapshot:
        ide_config = self._supervisor_client.get_ide_config()
        ida_mcp_config = self._supervisor_client.get_ida_mcp_config()
        ide_config.language = normalize_language(ide_config.language)
        return SettingsSnapshot(
            ide_config=ide_config,
            ida_mcp_config=ida_mcp_config,
        )

    def save(
        self,
        *,
        ide_updates: dict[str, object],
        ida_mcp_updates: dict[str, object],
    ) -> SettingsSnapshot:
        normalized_ide_updates = dict(ide_updates)
        normalized_ide_updates["language"] = normalize_language(
            normalized_ide_updates.get("language")
        )
        self._supervisor_client.update_ide_config(**normalized_ide_updates)
        self._supervisor_client.update_ida_mcp_config(**ida_mcp_updates)
        return self.load()

    def check(self) -> HealthReport:
        return self._supervisor_client.get_health_report()

    def check_installation(self) -> InstallationCheck:
        return self._supervisor_client.check_installation()

    def reinstall(self) -> InstallationActionResult:
        return self._supervisor_client.reinstall()
