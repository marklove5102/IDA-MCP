"""Gateway control via the gateway's own HTTP API.

All operations (status, start, stop) use the gateway's internal HTTP API
mounted at /internal/* on the gateway port, or direct TCP port probing.
Every HTTP request and response is logged via an optional log callback.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Callable

from .config_store import IdeConfigStore
from .models import GatewayState, GatewayStatus


def _error_status(message: str) -> GatewayStatus:
    return GatewayStatus(
        state=GatewayState.ERROR,
        alive=False,
        proxy_alive=False,
        enabled=True,
        host="127.0.0.1",
        port=11338,
        path="/mcp",
        last_error=message,
        raw={"error": message},
    )


class GatewayController:
    def __init__(
        self,
        config_store: IdeConfigStore | None = None,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.config_store = config_store or IdeConfigStore()
        self._log = log

    def _log_msg(self, msg: str) -> None:
        if self._log:
            self._log(msg)

    def _gateway_params(self) -> tuple[str, int, str]:
        config = self.config_store.load()
        host = config.gateway_host or "127.0.0.1"
        port = config.gateway_port or 11338
        path = config.gateway_path or "/mcp"
        return host, port, path

    def _internal_url(self, endpoint: str) -> str:
        host, port, _ = self._gateway_params()
        return f"http://{host}:{port}/internal{endpoint}"

    # ------------------------------------------------------------------
    # HTTP helpers with logging
    # ------------------------------------------------------------------
    def _tcp_port_open(self, host: str, port: int, timeout: float = 2.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def _http_get(
        self, url: str, timeout: float = 3.0
    ) -> tuple[int, dict[str, Any] | None]:
        """GET url, return (status_code, parsed_json_or_None)."""
        self._log_msg(f"GET {url}")
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read())
                code = resp.status
                self._log_msg(f"← {code} {json.dumps(body, ensure_ascii=False)[:300]}")
                return code, body
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            self._log_msg(f"← {exc.code} {raw[:300]}")
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, {"raw": raw}
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            self._log_msg(f"← error: {exc}")
            return 0, None

    def _http_post(
        self, url: str, body: dict[str, Any] | None = None, timeout: float = 10.0
    ) -> tuple[int, dict[str, Any] | None]:
        """POST url with json body, return (status_code, parsed_json_or_None)."""
        data = json.dumps(body or {}).encode("utf-8")
        self._log_msg(
            f"POST {url}  body={json.dumps(body or {}, ensure_ascii=False)[:200]}"
        )
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_body = json.loads(resp.read())
                code = resp.status
                self._log_msg(
                    f"← {code} {json.dumps(resp_body, ensure_ascii=False)[:300]}"
                )
                return code, resp_body
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            self._log_msg(f"← {exc.code} {raw[:300]}")
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, {"raw": raw}
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            self._log_msg(f"← error: {exc}")
            return 0, None

    # ------------------------------------------------------------------
    # Status — pure HTTP, no subprocess
    # ------------------------------------------------------------------
    def status(self) -> GatewayStatus:
        host, port, path = self._gateway_params()

        # 1. TCP port probe
        self._log_msg(f"TCP probe {host}:{port}...")
        if not self._tcp_port_open(host, port, timeout=2.0):
            self._log_msg(f"Port {port} closed — gateway stopped")
            return GatewayStatus(
                state=GatewayState.STOPPED,
                alive=False,
                proxy_alive=False,
                enabled=True,
                host=host,
                port=port,
                path=path,
                instance_count=0,
                last_error=None,
                raw={},
            )
        self._log_msg(f"Port {port} open")

        # 2. Healthz
        code, health = self._http_get(self._internal_url("/healthz"))
        if health is None:
            self._log_msg("healthz failed — gateway starting?")
            return GatewayStatus(
                state=GatewayState.STARTING,
                alive=True,
                proxy_alive=False,
                enabled=True,
                host=host,
                port=port,
                path=path,
                instance_count=0,
                last_error=None,
                raw={"port_open": True},
            )

        alive = bool(health.get("ok"))
        self._log_msg(f"healthz: ok={alive}")

        # 3. Instances
        _, instances_data = self._http_get(self._internal_url("/instances"))
        instance_list: list[dict[str, Any]] = []
        if isinstance(instances_data, list):
            instance_list = instances_data
        elif isinstance(instances_data, dict) and "instances" in instances_data:
            instance_list = instances_data["instances"]
        instance_count = len(instance_list)
        self._log_msg(f"instances: {instance_count}")

        # 4. Proxy status
        _, proxy_data = self._http_get(self._internal_url("/proxy_status"))
        proxy_alive = (
            bool(proxy_data.get("alive")) if isinstance(proxy_data, dict) else alive
        )

        state = GatewayState.RUNNING if alive else GatewayState.STOPPED
        self._log_msg(
            f"Status: {state.value}, alive={alive}, proxy={proxy_alive}, instances={instance_count}"
        )
        return GatewayStatus(
            state=state,
            alive=alive,
            proxy_alive=proxy_alive,
            enabled=True,
            host=host,
            port=port,
            path=path,
            instance_count=instance_count,
            instances=instance_list,
            last_error=health.get("error") if isinstance(health, dict) else None,
            raw=health,
        )

    # ------------------------------------------------------------------
    # Start — HTTP if already running, subprocess otherwise
    # ------------------------------------------------------------------
    def start(self) -> GatewayStatus:
        host, port, _ = self._gateway_params()

        self._log_msg(f"Checking if gateway is already running on {host}:{port}...")
        if self._tcp_port_open(host, port, timeout=1.0):
            self._log_msg("Gateway already running, fetching status...")
            return self.status()

        self._log_msg("Port not open, launching gateway via subprocess...")
        return self._subprocess_start()

    # ------------------------------------------------------------------
    # Stop — POST /internal/shutdown (never force)
    # ------------------------------------------------------------------
    def stop(self, force: bool = False) -> GatewayStatus:
        host, port, path = self._gateway_params()

        self._log_msg(f"Checking {host}:{port} before stop...")
        if not self._tcp_port_open(host, port, timeout=1.0):
            self._log_msg("Port closed — gateway already stopped")
            return GatewayStatus(
                state=GatewayState.STOPPED,
                alive=False,
                proxy_alive=False,
                enabled=True,
                host=host,
                port=port,
                path=path,
                instance_count=0,
                last_error=None,
                raw={},
            )

        # Send shutdown request — never force, let the server refuse if instances exist
        code, result = self._http_post(self._internal_url("/shutdown"), body={})
        if code == 409:
            # Instances still registered — shutdown refused
            msg = (result or {}).get("error", "Shutdown refused")
            count = (result or {}).get("instance_count", "?")
            self._log_msg(f"Shutdown refused: {msg} (instances: {count})")
            return self.status()

        if code == 0 or result is None:
            self._log_msg("Shutdown request failed (network error)")
            return self.status()

        # Shutdown accepted — wait for port to close
        self._log_msg("Shutdown accepted, waiting for port to close...")
        for i in range(20):
            if not self._tcp_port_open(host, port, timeout=0.5):
                self._log_msg("Gateway stopped (port closed)")
                break
            time.sleep(0.25)

        return self.status()

    def restart(self, force: bool = False) -> GatewayStatus:
        stopped = self.stop(force=force)
        if stopped.state == GatewayState.ERROR:
            return stopped
        return self.start()

    # ------------------------------------------------------------------
    # Subprocess fallback for starting
    # ------------------------------------------------------------------
    def _subprocess_start(self) -> GatewayStatus:
        config = self.config_store.load()
        if not config.python_path or not config.plugin_dir:
            msg = "Set python_path and plugin_dir before starting the gateway."
            self._log_msg(f"ERROR: {msg}")
            return _error_status(msg)

        python_path = Path(config.python_path)
        plugin_dir = Path(config.plugin_dir)
        if not python_path.exists() or not plugin_dir.exists():
            msg = f"python_path ({python_path}) or plugin_dir ({plugin_dir}) does not exist."
            self._log_msg(f"ERROR: {msg}")
            return _error_status(msg)

        env = dict(os.environ)
        current = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(plugin_dir) if not current else f"{plugin_dir}{os.pathsep}{current}"
        )

        script = (
            "import json; from ida_mcp import control; "
            "print(json.dumps(control.ensure_gateway_running(), ensure_ascii=False, default=str))"
        )
        cmd = [str(python_path), "-c", script]
        self._log_msg(f"$ {' '.join(cmd)}")
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(config.request_timeout, 10),
                env=env,
            )
        except Exception as exc:
            self._log_msg(f"Subprocess error: {exc}")
            return _error_status(str(exc))

        self._log_msg(f"stdout: {completed.stdout.strip()[:500]}")
        if completed.stderr.strip():
            self._log_msg(f"stderr: {completed.stderr.strip()[:500]}")

        if completed.returncode != 0:
            msg = (
                completed.stderr or completed.stdout
            ).strip() or "gateway start failed"
            self._log_msg(f"Subprocess exit code {completed.returncode}")
            return _error_status(msg)

        try:
            json.loads(completed.stdout)
        except json.JSONDecodeError:
            return _error_status(
                completed.stdout.strip() or "gateway returned invalid JSON"
            )

        self._log_msg("Gateway launched, checking status...")
        return self.status()
