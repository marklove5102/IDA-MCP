"""Simple in-process client for the local supervisor MVP."""

from __future__ import annotations

from typing import Callable

from supervisor.api import create_manager
from supervisor.models import (
    HealthReport,
    IdaMcpConfig,
    InstallationActionResult,
    InstallationCheck,
    IdeConfig,
    SupervisorSnapshot,
)


class SupervisorClient:
    def __init__(self) -> None:
        self._manager = create_manager()

    def get_snapshot(
        self, log: Callable[[str], None] | None = None
    ) -> SupervisorSnapshot:
        return self._manager.get_snapshot(log=log)

    def get_health_report(
        self, log: Callable[[str], None] | None = None
    ) -> HealthReport:
        return self._manager.get_health_report(log=log)

    def get_ide_config(self) -> IdeConfig:
        return self._manager.get_ide_config()

    def get_config(self) -> IdeConfig:
        return self.get_ide_config()

    def get_ida_mcp_config(self) -> IdaMcpConfig:
        return self._manager.get_ida_mcp_config()

    def get_ide_config_store_info(self):
        return self._manager.get_ide_config_store_info()

    def get_ida_mcp_config_store_info(self):
        return self._manager.get_ida_mcp_config_store_info()

    def start_gateway(
        self, log: Callable[[str], None] | None = None
    ) -> SupervisorSnapshot:
        self._manager.start_gateway(log=log)
        return self.get_snapshot(log=log)

    def stop_gateway(
        self, *, log: Callable[[str], None] | None = None
    ) -> SupervisorSnapshot:
        self._manager.stop_gateway(log=log)
        return self.get_snapshot(log=log)

    def update_ide_config(self, **updates: object) -> IdeConfig:
        return self._manager.update_ide_config(**updates)

    def update_config(self, **updates: object) -> IdeConfig:
        return self.update_ide_config(**updates)

    def update_ida_mcp_config(self, **updates: object) -> IdaMcpConfig:
        return self._manager.update_ida_mcp_config(**updates)

    def check_installation(self) -> InstallationCheck:
        return self._manager.check_installation()

    def repair_installation(self) -> InstallationActionResult:
        return self._manager.repair_installation()

    def reinstall(self, *, on_progress=None) -> InstallationActionResult:
        return self._manager.reinstall(on_progress=on_progress)
