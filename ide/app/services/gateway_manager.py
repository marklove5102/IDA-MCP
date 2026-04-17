"""Gateway lifecycle manager — worker scheduling, log routing, and snapshot dispatch."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QThread, Signal

from app.services.supervisor_client import SupervisorClient
from supervisor.models import SupervisorSnapshot


class _GatewayWorker(QThread):
    progress = Signal(str)
    finished = Signal(object)  # SupervisorSnapshot

    def __init__(
        self, action: str, supervisor_client: SupervisorClient, parent=None
    ) -> None:
        super().__init__(parent)
        self._action = action
        self._supervisor_client = supervisor_client

    def run(self) -> None:
        log = self.progress.emit
        try:
            if self._action == "refresh":
                log("--- Refreshing status ---")
                snapshot = self._supervisor_client.get_snapshot(log=log)
            elif self._action == "start":
                log("--- Starting gateway ---")
                snapshot = self._supervisor_client.start_gateway(log=log)
            elif self._action == "stop":
                log("--- Stopping gateway ---")
                snapshot = self._supervisor_client.stop_gateway(log=log)
            else:
                raise ValueError(f"Unsupported gateway action: {self._action}")
            self.finished.emit(snapshot)
        except Exception as exc:
            log(f"Error: {exc}")
            try:
                self.finished.emit(self._supervisor_client.get_snapshot(log=log))
            except Exception:
                self.finished.emit(None)


class GatewayManager(QObject):
    """Manages gateway lifecycle operations via background workers.

    Signals:
        snapshot_ready(SupervisorSnapshot): emitted when a fresh snapshot arrives.
        log_message(str): emitted for each gateway log line.
        busy_changed(bool): emitted when a worker starts/stops.
    """

    snapshot_ready = Signal(object)
    log_message = Signal(str)
    busy_changed = Signal(bool)

    def __init__(
        self,
        supervisor_client: SupervisorClient,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._client = supervisor_client
        self._worker: _GatewayWorker | None = None
        self._snapshot: SupervisorSnapshot | None = None
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self.refresh)

    @property
    def snapshot(self) -> SupervisorSnapshot | None:
        return self._snapshot

    @property
    def is_busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def refresh(self) -> None:
        """Refresh gateway status via a background worker."""
        if self.is_busy:
            return
        self._start_worker("refresh")

    def start_gateway(self) -> None:
        if self.is_busy:
            return
        self._start_worker("start")

    def stop_gateway(self) -> None:
        if self.is_busy:
            return
        self._start_worker("stop")

    def _start_worker(self, action: str) -> None:
        self.busy_changed.emit(True)
        worker = _GatewayWorker(action, self._client, parent=self)
        self._worker = worker
        worker.progress.connect(self._on_log)
        worker.finished.connect(self._on_finished)
        worker.start()

    def _on_log(self, message: str) -> None:
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_message.emit(f"[{timestamp}] {message}")

    def _on_finished(self, snapshot: object) -> None:
        self.busy_changed.emit(False)
        from supervisor.models import SupervisorSnapshot

        if isinstance(snapshot, SupervisorSnapshot):
            self._snapshot = snapshot
            self.snapshot_ready.emit(snapshot)

            if snapshot.gateway.alive:
                if not self._auto_refresh_timer.isActive():
                    self._auto_refresh_timer.start(10000)
            else:
                self._auto_refresh_timer.stop()
