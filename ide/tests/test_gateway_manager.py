import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from app.services.gateway_manager import GatewayManager
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
    def __init__(self, language: str = "en") -> None:
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

    def get_snapshot(self, *, log=None) -> SupervisorSnapshot:
        return _build_snapshot(self.ide_config)

    def start_gateway(self, *, log=None) -> SupervisorSnapshot:
        return _build_snapshot(self.ide_config, alive=True, state=GatewayState.RUNNING)

    def stop_gateway(self, *, log=None) -> SupervisorSnapshot:
        return _build_snapshot(self.ide_config)


class _FakeWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    instances: list["_FakeWorker"] = []

    def __init__(
        self, action: str, supervisor_client: SupervisorClient, parent=None
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.supervisor_client = supervisor_client
        self.started = False
        self._running = False
        type(self).instances.append(self)

    def start(self) -> None:
        self.started = True
        self._running = True

    def isRunning(self) -> bool:
        return self._running


def _build_snapshot(
    ide_config: IdeConfig,
    *,
    alive: bool = False,
    state: GatewayState = GatewayState.STOPPED,
) -> SupervisorSnapshot:
    gateway_summary = "Gateway running" if alive else "Gateway stopped"
    gateway_health = HealthState.OK if alive else HealthState.WARNING
    supervisor = ComponentHealth("supervisor", HealthState.OK, "Supervisor ready")
    gateway = ComponentHealth("gateway", gateway_health, gateway_summary)
    environment = ComponentHealth("environment", HealthState.OK, "Environment ready")
    gateway_status = GatewayStatus(
        state=state,
        alive=alive,
        proxy_alive=alive,
        enabled=True,
        host="127.0.0.1",
        port=11338,
        path="/mcp",
        instance_count=1 if alive else 0,
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
        config=ide_config,
        gateway_status=gateway_status,
        environment_probe=env,
    )
    return SupervisorSnapshot(
        config=ide_config,
        config_store=ConfigStoreInfo(path="ide.json", exists=True),
        gateway=gateway_status,
        environment=env,
        health=report,
    )


def test_gateway_manager_worker_signals_drive_busy_logs_and_snapshot(
    monkeypatch,
) -> None:
    _app()
    _FakeWorker.instances.clear()
    monkeypatch.setattr("app.services.gateway_manager._GatewayWorker", _FakeWorker)
    client = _StubSupervisorClient()
    manager = GatewayManager(client)
    busy_states: list[bool] = []
    log_messages: list[str] = []
    snapshots: list[SupervisorSnapshot] = []
    manager.busy_changed.connect(busy_states.append)
    manager.log_message.connect(log_messages.append)
    manager.snapshot_ready.connect(snapshots.append)

    manager.refresh()

    worker = _FakeWorker.instances[-1]
    assert worker.action == "refresh"
    assert worker.started is True
    assert manager.is_busy is True
    assert busy_states == [True]

    worker.progress.emit("refresh step")

    assert len(log_messages) == 1
    assert log_messages[0].endswith("refresh step")
    assert log_messages[0].startswith("[")

    worker._running = False
    finished_snapshot = _build_snapshot(
        client.ide_config,
        alive=True,
        state=GatewayState.RUNNING,
    )
    worker.finished.emit(finished_snapshot)

    assert manager.is_busy is False
    assert manager.snapshot is finished_snapshot
    assert snapshots == [finished_snapshot]
    assert busy_states == [True, False]
    assert manager._auto_refresh_timer.isActive() is True
    assert manager._auto_refresh_timer.interval() == 10000


def test_gateway_manager_finished_stops_auto_refresh_when_gateway_is_down() -> None:
    _app()
    client = _StubSupervisorClient()
    manager = GatewayManager(client)

    manager._on_finished(
        _build_snapshot(client.ide_config, alive=True, state=GatewayState.RUNNING)
    )
    assert manager._auto_refresh_timer.isActive() is True

    stopped_snapshot = _build_snapshot(
        client.ide_config, alive=False, state=GatewayState.STOPPED
    )
    manager._on_finished(stopped_snapshot)

    assert manager.snapshot is stopped_snapshot
    assert manager._auto_refresh_timer.isActive() is False
