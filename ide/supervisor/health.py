"""Health aggregation for the local supervisor MVP."""

from __future__ import annotations

from .models import (
    ComponentHealth,
    EnvironmentProbe,
    GatewayStatus,
    HealthReport,
    HealthState,
    IdeConfig,
)


def _gateway_health(status: GatewayStatus) -> ComponentHealth:
    if status.alive:
        state = HealthState.OK
        summary = "gateway is reachable"
    elif status.last_error:
        state = HealthState.ERROR
        summary = status.last_error
    else:
        state = HealthState.WARNING
        summary = "gateway is not running"
    return ComponentHealth(
        name="gateway",
        state=state,
        summary=summary,
        details={
            "instances": status.instance_count,
            "host": status.host,
            "port": status.port,
            "path": status.path,
            "proxy_alive": status.proxy_alive,
        },
    )


def _environment_health(probe: EnvironmentProbe) -> ComponentHealth:
    if probe.ida_mcp_importable and probe.python_executable:
        state = HealthState.OK
        summary = "basic environment looks usable"
    elif probe.python_executable:
        state = HealthState.WARNING
        summary = "python detected but ida_mcp import failed"
    else:
        state = HealthState.ERROR
        summary = "python executable not detected"
    return ComponentHealth(
        name="environment",
        state=state,
        summary=summary,
        details={
            "python_executable": probe.python_executable,
            "python_version": probe.python_version,
            "ida_mcp_importable": probe.ida_mcp_importable,
            "ida_path_candidates": probe.ida_path_candidates,
            "ida_python_candidates": probe.ida_python_candidates,
            "warnings": probe.warnings,
        },
    )


def _supervisor_health(config: IdeConfig) -> ComponentHealth:
    return ComponentHealth(
        name="supervisor",
        state=HealthState.OK,
        summary="supervisor MVP is available",
        details={
            "auto_start_gateway": config.auto_start_gateway,
            "request_timeout": config.request_timeout,
        },
    )


def build_health_report(
    config: IdeConfig,
    gateway_status: GatewayStatus,
    environment_probe: EnvironmentProbe,
) -> HealthReport:
    return HealthReport(
        supervisor=_supervisor_health(config),
        gateway=_gateway_health(gateway_status),
        environment=_environment_health(environment_probe),
        config=config,
        gateway_status=gateway_status,
        environment_probe=environment_probe,
    )
