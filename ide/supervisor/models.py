"""Data models for the local supervisor MVP."""

from __future__ import annotations

import locale
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class HealthState(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class GatewayState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Canonical default values — single source of truth
# ---------------------------------------------------------------------------
DEFAULT_GATEWAY_HOST = "127.0.0.1"
DEFAULT_GATEWAY_PORT = 11338
DEFAULT_GATEWAY_PATH = "/mcp"
DEFAULT_HTTP_HOST = "0.0.0.0"
DEFAULT_IDA_HOST = "127.0.0.1"
DEFAULT_IDA_PORT = 10000
DEFAULT_SERVER_NAME = "IDA-MCP"


def _default_language() -> str:
    preferred = locale.getlocale()[0] or ""
    if preferred.lower().startswith("zh"):
        return "zh"
    return "en"


@dataclass(slots=True)
class IdeConfig:
    gateway_host: str = DEFAULT_GATEWAY_HOST
    gateway_port: int = DEFAULT_GATEWAY_PORT
    gateway_path: str = DEFAULT_GATEWAY_PATH
    request_timeout: int = 30
    auto_start_gateway: bool = False
    python_path: str | None = None
    plugin_dir: str | None = None
    ida_path: str | None = None
    ida_python: str | None = None
    language: str = field(default_factory=_default_language)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "IdeConfig":
        if not data:
            return cls()
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass(slots=True)
class IdaMcpConfig:
    enable_stdio: bool = False
    enable_http: bool = True
    enable_unsafe: bool = True
    wsl_path_bridge: bool = False
    http_host: str = DEFAULT_HTTP_HOST
    http_port: int = DEFAULT_GATEWAY_PORT
    http_path: str = DEFAULT_GATEWAY_PATH
    ida_default_port: int = DEFAULT_IDA_PORT
    ida_host: str = DEFAULT_IDA_HOST
    ida_path: str | None = None
    ida_python: str | None = None
    open_in_ida_bundle_dir: str | None = None
    open_in_ida_autonomous: bool = True
    auto_start: bool = False
    server_name: str = DEFAULT_SERVER_NAME
    request_timeout: int = 30
    debug: bool = False
    config_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("config_path", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "IdaMcpConfig":
        if not data:
            return cls()
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass(slots=True)
class ConfigStoreInfo:
    path: str
    exists: bool


@dataclass(slots=True)
class GatewayStatus:
    state: GatewayState
    alive: bool
    proxy_alive: bool
    enabled: bool
    host: str
    port: int
    path: str
    instance_count: int = 0
    instances: list[dict[str, Any]] = field(default_factory=list)
    last_error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EnvironmentProbe:
    python_executable: str | None
    python_version: str
    ida_mcp_importable: bool
    ida_mcp_location: str | None
    ida_path_candidates: list[str] = field(default_factory=list)
    ida_python_candidates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InstallationCheck:
    plugin_dir: str | None
    plugin_dir_exists: bool
    config_path: str | None
    config_exists: bool
    python_executable: str | None
    python_exists: bool
    ida_mcp_py_exists: bool
    ida_mcp_package_exists: bool
    summary: str
    requirements_path: str | None = None
    requirements: list[str] = field(default_factory=list)
    installed_requirements: dict[str, str] = field(default_factory=dict)
    missing_requirements: list[str] = field(default_factory=list)
    unresolved_requirements: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InstallationActionResult:
    action: str
    ok: bool
    summary: str
    check: InstallationCheck
    config_path: str | None = None
    created: bool = False
    already_exists: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ComponentHealth:
    name: str
    state: HealthState
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HealthReport:
    supervisor: ComponentHealth
    gateway: ComponentHealth
    environment: ComponentHealth
    config: IdeConfig
    gateway_status: GatewayStatus
    environment_probe: EnvironmentProbe


@dataclass(slots=True)
class SupervisorSnapshot:
    config: IdeConfig
    config_store: ConfigStoreInfo
    gateway: GatewayStatus
    environment: EnvironmentProbe
    health: HealthReport
