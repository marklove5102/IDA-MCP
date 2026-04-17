"""Unified supervisor manager for config, gateway and health."""

from __future__ import annotations

from typing import Callable

from shared.ida_mcp_config import IdaMcpConfigStore

from .config_store import IdeConfigStore
from .gateway_controller import GatewayController
from .health import build_health_report
from .installer import EnvironmentInstaller
from .models import (
    EnvironmentProbe,
    GatewayStatus,
    HealthReport,
    IdaMcpConfig,
    InstallationActionResult,
    InstallationCheck,
    IdeConfig,
    SupervisorSnapshot,
)


class SupervisorManager:
    def __init__(
        self,
        config_store: IdeConfigStore | None = None,
        ida_mcp_config_store: IdaMcpConfigStore | None = None,
        installer: EnvironmentInstaller | None = None,
        gateway_controller: GatewayController | None = None,
    ) -> None:
        self.config_store = config_store or IdeConfigStore()
        self.ida_mcp_config_store = ida_mcp_config_store
        self.installer = installer or EnvironmentInstaller()
        self.gateway_controller = gateway_controller or GatewayController(
            self.config_store
        )

    def _get_ida_mcp_config_store(self) -> IdaMcpConfigStore:
        if self.ida_mcp_config_store is not None:
            return self.ida_mcp_config_store
        config = self.config_store.load()
        return IdaMcpConfigStore(plugin_dir=config.plugin_dir)

    def get_ide_config(self) -> IdeConfig:
        return self.config_store.load()

    def get_config(self) -> IdeConfig:
        return self.get_ide_config()

    def get_ida_mcp_config(self) -> IdaMcpConfig:
        return self._get_ida_mcp_config_store().load()

    def _effective_python_path(self) -> str | None:
        return self.get_ida_mcp_config().ida_python

    def get_ide_config_store_info(self):
        return self.config_store.info()

    def get_ida_mcp_config_store_info(self):
        return self._get_ida_mcp_config_store().info()

    def update_ide_config(self, **updates: object) -> IdeConfig:
        return self.config_store.update(**updates)

    def update_config(self, **updates: object) -> IdeConfig:
        return self.update_ide_config(**updates)

    def update_ida_mcp_config(self, **updates: object) -> IdaMcpConfig:
        return self._get_ida_mcp_config_store().update(**updates)

    def probe_environment(self) -> EnvironmentProbe:
        config = self.get_ide_config()
        return self.installer.probe(plugin_dir=config.plugin_dir)

    def check_installation(self) -> InstallationCheck:
        config = self.get_ide_config()
        return self.installer.check_installation(
            plugin_dir=config.plugin_dir,
            python_executable=self._effective_python_path(),
            config_path=None,
        )

    def repair_installation(self) -> InstallationActionResult:
        config = self.get_ide_config()
        return self.installer.repair_config(
            plugin_dir=config.plugin_dir,
            python_executable=self._effective_python_path(),
            config_path=None,
        )

    def reinstall(
        self, *, on_progress: Callable[[str], None] | None = None
    ) -> InstallationActionResult:
        from .install_runner import run_install

        config = self.get_ide_config()
        ida_mcp_config = self.get_ida_mcp_config()
        python_path = self._effective_python_path()
        if not python_path:
            return InstallationActionResult(
                action="install",
                ok=False,
                summary="no Python executable configured",
                check=self.installer.check_installation(
                    plugin_dir=config.plugin_dir,
                    python_executable=None,
                    config_path=None,
                ),
                warnings=["python_path not configured"],
            )

        config_dict = ida_mcp_config.to_dict()
        return run_install(
            python_executable=python_path,
            ida_path=ida_mcp_config.ida_path,
            plugin_dir=config.plugin_dir,
            ida_mcp_config_dict=config_dict,
            on_progress=on_progress,
        )

    def _controller_with_log(
        self, log: Callable[[str], None] | None
    ) -> GatewayController:
        """Return a controller, optionally with log routing.

        When *log* is None, returns the injected ``self.gateway_controller``
        so that tests and callers can substitute their own controller.

        When *log* is provided, creates a fresh controller sharing the same
        config_store and python_path so that log callbacks don't cross
        between concurrent calls.
        """
        if log is None:
            return self.gateway_controller
        return GatewayController(
            self.config_store,
            log=log,
            python_path=self._effective_python_path(),
        )

    def get_gateway_status(
        self, log: Callable[[str], None] | None = None
    ) -> GatewayStatus:
        return self._controller_with_log(log).status()

    def start_gateway(self, log: Callable[[str], None] | None = None) -> GatewayStatus:
        return self._controller_with_log(log).start()

    def stop_gateway(self, log: Callable[[str], None] | None = None) -> GatewayStatus:
        return self._controller_with_log(log).stop()

    def get_health_report(
        self, log: Callable[[str], None] | None = None
    ) -> HealthReport:
        config = self.get_config()
        gateway = self.get_gateway_status(log=log)
        environment = self.probe_environment()
        return build_health_report(config, gateway, environment)

    def get_snapshot(
        self, log: Callable[[str], None] | None = None
    ) -> SupervisorSnapshot:
        config = self.get_config()
        gateway = self.get_gateway_status(log=log)
        environment = self.probe_environment()
        health = build_health_report(config, gateway, environment)
        return SupervisorSnapshot(
            config=config,
            config_store=self.config_store.info(),
            gateway=gateway,
            environment=environment,
            health=health,
        )
