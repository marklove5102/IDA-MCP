import os
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.services.supervisor_client import SupervisorClient
from supervisor.models import (
    ComponentHealth,
    ConfigStoreInfo,
    EnvironmentProbe,
    GatewayState,
    GatewayStatus,
    HealthReport,
    HealthState,
    IdaMcpConfig,
    IdeConfig,
    InstallationCheck,
    SupervisorSnapshot,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _StubSupervisorClient(SupervisorClient):
    def __init__(self, language: str = "zh") -> None:
        self.ide_config = IdeConfig(language=language, plugin_dir="E:/plugins")
        self.ida_mcp_config = IdaMcpConfig(ida_path="E:/IDA/ida64.exe")

    def get_ide_config(self) -> IdeConfig:
        return self.ide_config

    def get_ida_mcp_config(self) -> IdaMcpConfig:
        return self.ida_mcp_config

    def get_ide_config_store_info(self) -> ConfigStoreInfo:
        return ConfigStoreInfo(path="ide.json", exists=True)

    def get_ida_mcp_config_store_info(self) -> ConfigStoreInfo:
        return ConfigStoreInfo(path="config.conf", exists=True)

    def check_installation(self) -> InstallationCheck:
        return InstallationCheck(
            plugin_dir="E:/plugins",
            plugin_dir_exists=True,
            config_path="E:/plugins/ida_mcp/config.conf",
            config_exists=True,
            python_executable="E:/IDA/python.exe",
            python_exists=True,
            ida_mcp_py_exists=True,
            ida_mcp_package_exists=True,
            summary="ok",
            requirements_path="E:/DM/IDA-MCP/requirements.txt",
            requirements=["fastmcp", "pytest"],
            installed_requirements={"fastmcp": "1.0.0"},
            missing_requirements=["pytest"],
        )

    def get_mcp_servers(self) -> list:
        return []

    def get_skills(self) -> list:
        return []

    def get_skills_dir(self):
        return Path("E:/plugins/ida_mcp/skills")

    def get_snapshot(self, *, log=None) -> SupervisorSnapshot:
        return self._build_snapshot()

    def start_gateway(self, *, log=None) -> SupervisorSnapshot:
        return self._build_snapshot()

    def stop_gateway(self, *, log=None) -> SupervisorSnapshot:
        return self._build_snapshot()

    def _build_snapshot(self) -> SupervisorSnapshot:
        supervisor = ComponentHealth("supervisor", HealthState.OK, "Supervisor ready")
        gateway = ComponentHealth("gateway", HealthState.WARNING, "Gateway stopped")
        environment = ComponentHealth(
            "environment", HealthState.OK, "Environment ready"
        )
        gateway_status = GatewayStatus(
            state=GatewayState.STOPPED,
            alive=False,
            proxy_alive=False,
            enabled=True,
            host="127.0.0.1",
            port=11338,
            path="/mcp",
            instance_count=0,
        )
        env = EnvironmentProbe(
            python_executable="python",
            python_version="3.12",
            ida_mcp_importable=True,
            ida_mcp_location="E:/DM/IDA-MCP",
            ida_path_candidates=["E:/IDA/ida64.exe"],
            warnings=[],
        )
        report = HealthReport(
            supervisor=supervisor,
            gateway=gateway,
            environment=environment,
            config=self.ide_config,
            gateway_status=gateway_status,
            environment_probe=env,
        )
        return SupervisorSnapshot(
            config=self.ide_config,
            config_store=ConfigStoreInfo(path="ide.json", exists=True),
            gateway=gateway_status,
            environment=env,
            health=report,
        )


def test_main_window_retranslates_core_shell_labels(monkeypatch) -> None:
    _app()
    monkeypatch.setattr(
        "app.services.gateway_manager.GatewayManager.refresh", lambda self: None
    )
    client = _StubSupervisorClient(language="zh")
    window = MainWindow(client)

    # Inject a snapshot through the public signal so the UI updates
    # without coupling to the manager's internal worker lifecycle.
    window._gateway._snapshot = client.get_snapshot()
    window._gateway.snapshot_ready.emit(client.get_snapshot())

    assert window._activity_items["chat"].toolTip() == "聊天"
    assert window._status_buttons["toggle_gateway"].text() == "启动 Gateway"
    assert window._status_card_titles["environment"].text() == "环境"
    assert window.statusBar().currentMessage() == "快照已刷新"

    window._settings_view.language_changed.emit("en")

    assert window._activity_items["chat"].toolTip() == "Chat"
    assert window._status_buttons["toggle_gateway"].text() == "Start Gateway"
    assert window._status_card_titles["environment"].text() == "Environment"

    window.close()


def test_main_window_busy_changed_disables_status_buttons(monkeypatch) -> None:
    _app()
    monkeypatch.setattr(
        "app.services.gateway_manager.GatewayManager.refresh", lambda self: None
    )
    client = _StubSupervisorClient(language="en")
    window = MainWindow(client)

    refresh_button = window._status_buttons["refresh"]
    toggle_button = window._status_buttons["toggle_gateway"]

    assert refresh_button.isEnabled() is True
    assert toggle_button.isEnabled() is True

    window._gateway.busy_changed.emit(True)

    assert refresh_button.isEnabled() is False
    assert toggle_button.isEnabled() is False

    window._gateway.busy_changed.emit(False)

    assert refresh_button.isEnabled() is True
    assert toggle_button.isEnabled() is True

    window.close()
