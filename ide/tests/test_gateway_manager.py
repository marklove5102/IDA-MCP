"""Tests for GatewayManager — exercises public signals and observable state only.

Tests drive the manager through its public API (refresh / start_gateway /
stop_gateway) and verify behavior via the signals it emits and the state
it exposes (is_busy, snapshot, auto_refresh_timer).  Worker creation is
monkeypatched with a stub so no real threads are spawned.
"""

import os
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Stub supervisor client
# ---------------------------------------------------------------------------

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

    def get_mcp_servers(self) -> list:
        return []

    def get_skills(self) -> list:
        return []

    def get_skills_dir(self):
        return Path("E:/plugins/ida_mcp/skills")

    def get_snapshot(self, *, log=None) -> SupervisorSnapshot:
        return _build_snapshot(self.ide_config)

    def start_gateway(self, *, log=None) -> SupervisorSnapshot:
        return _build_snapshot(self.ide_config, alive=True, state=GatewayState.RUNNING)

    def stop_gateway(self, *, log=None) -> SupervisorSnapshot:
        return _build_snapshot(self.ide_config)


# ---------------------------------------------------------------------------
# Fake worker — QObject stub with matching signals, records calls
# ---------------------------------------------------------------------------

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

    def quit(self) -> None:
        self._running = False

    def wait(self, msecs: int = 0) -> bool:  # noqa: ARG002
        self._running = False
        return True


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------

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


# ===================================================================
# Tests — all driven through public API + signal emission
# ===================================================================

def test_refresh_drives_busy_snapshot_and_log_signals(monkeypatch) -> None:
    """refresh() → busy True → worker emits progress/finished → busy False."""
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

    # 1. Start a refresh.
    manager.refresh()
    worker = _FakeWorker.instances[-1]
    assert worker.action == "refresh"
    assert worker.started is True
    assert manager.is_busy is True
    assert busy_states == [True]

    # 2. Emit progress from the worker.
    worker.progress.emit("refresh step")
    assert len(log_messages) == 1
    assert log_messages[0].endswith("refresh step")
    assert log_messages[0].startswith("[")

    # 3. Worker finishes — mark not running, then emit finished.
    worker._running = False
    finished_snapshot = _build_snapshot(
        client.ide_config,
        alive=True,
        state=GatewayState.RUNNING,
    )
    worker.finished.emit(finished_snapshot)

    # 4. Manager transitions to not-busy and delivers the snapshot.
    assert manager.is_busy is False
    assert manager.snapshot is finished_snapshot
    assert snapshots == [finished_snapshot]
    assert busy_states == [True, False]
    assert manager._auto_refresh_timer.isActive() is True
    assert manager._auto_refresh_timer.interval() == 10000


def test_stopped_snapshot_disables_auto_refresh(monkeypatch) -> None:
    """When a finished snapshot shows gateway stopped, auto-refresh stops."""
    _app()
    _FakeWorker.instances.clear()
    monkeypatch.setattr("app.services.gateway_manager._GatewayWorker", _FakeWorker)

    client = _StubSupervisorClient()
    manager = GatewayManager(client)

    # First refresh — gateway running → auto-refresh starts.
    manager.refresh()
    running_worker = _FakeWorker.instances[-1]
    running_worker._running = False
    running_snapshot = _build_snapshot(
        client.ide_config, alive=True, state=GatewayState.RUNNING
    )
    running_worker.finished.emit(running_snapshot)
    assert manager._auto_refresh_timer.isActive() is True

    # Second refresh — gateway stopped → auto-refresh stops.
    manager.refresh()
    stopped_worker = _FakeWorker.instances[-1]
    stopped_worker._running = False
    stopped_snapshot = _build_snapshot(
        client.ide_config, alive=False, state=GatewayState.STOPPED
    )
    stopped_worker.finished.emit(stopped_snapshot)

    assert manager.snapshot is stopped_snapshot
    assert manager._auto_refresh_timer.isActive() is False


def test_stale_finished_does_not_delete_newer_worker(monkeypatch) -> None:
    """A late finished signal from worker A must not delete the newer worker B."""
    _app()
    _FakeWorker.instances.clear()
    monkeypatch.setattr("app.services.gateway_manager._GatewayWorker", _FakeWorker)

    client = _StubSupervisorClient()
    manager = GatewayManager(client)
    busy_states: list[bool] = []
    manager.busy_changed.connect(busy_states.append)

    # Start worker A.
    manager.refresh()
    worker_a = _FakeWorker.instances[-1]

    # Worker A finishes running but finished signal has NOT been emitted yet.
    worker_a._running = False

    # Start worker B (A was cleaned up because it's no longer running).
    manager.refresh()
    worker_b = _FakeWorker.instances[-1]
    assert worker_b is not worker_a

    # Now the stale worker A's finished signal arrives (queued delivery).
    snap_a = _build_snapshot(client.ide_config)
    worker_a.finished.emit(snap_a)

    # Worker B should still be alive and well.
    assert manager._worker is worker_b
    assert manager.is_busy is True
    # busy_states: [True (A start), True (B start)] — no False from stale A.
    assert busy_states == [True, True]

    # Worker B finishes normally.
    worker_b._running = False
    snap_b = _build_snapshot(client.ide_config, alive=True, state=GatewayState.RUNNING)
    worker_b.finished.emit(snap_b)
    assert manager.is_busy is False
    assert manager.snapshot is snap_b
