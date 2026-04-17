from app.i18n import I18n
from app.presenters.main_window_presenter import build_main_window_view_model
from supervisor.models import (
    ComponentHealth,
    ConfigStoreInfo,
    EnvironmentProbe,
    GatewayState,
    GatewayStatus,
    HealthReport,
    HealthState,
    IdeConfig,
    SupervisorSnapshot,
)


def test_main_window_view_model_builds_cards_and_tree_rows() -> None:
    i18n = I18n("en")
    config = IdeConfig(
        plugin_dir="E:/plugins",
        notes="pending setup",
        request_timeout=40,
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
    environment = EnvironmentProbe(
        python_executable="python",
        python_version="3.12",
        ida_mcp_importable=True,
        ida_mcp_location="E:/DM/IDA-MCP",
        ida_path_candidates=["E:/IDA/ida64.exe"],
        warnings=["IDA not configured"],
    )
    snapshot = SupervisorSnapshot(
        config=config,
        config_store=ConfigStoreInfo(path="ide.json", exists=True),
        gateway=gateway_status,
        environment=environment,
        health=HealthReport(
            supervisor=ComponentHealth(
                "supervisor", HealthState.OK, "Supervisor ready"
            ),
            gateway=ComponentHealth("gateway", HealthState.WARNING, "Gateway stopped"),
            environment=ComponentHealth(
                "environment", HealthState.OK, "Environment ready"
            ),
            config=config,
            gateway_status=gateway_status,
            environment_probe=environment,
        ),
    )

    view_model = build_main_window_view_model(snapshot, i18n.t)

    assert [card.key for card in view_model.status_cards] == [
        "supervisor",
        "gateway",
        "environment",
        "instances",
    ]
    assert view_model.status_cards[1].state_property == "warning"
    assert "State: stopped" in view_model.status_cards[1].details
    assert view_model.ida_rows[0].label == "Gateway state"
    assert view_model.ida_rows[0].value == "stopped"
    assert view_model.plan_rows[0].value == "not started"
