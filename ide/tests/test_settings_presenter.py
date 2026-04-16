from app.i18n import I18n
from app.presenters.settings_presenter import (
    SettingsFormState,
    build_check_message,
    effective_install_python_path,
    form_state_to_updates,
    snapshot_to_form_state,
)
from app.services.settings_service import SettingsSnapshot
from supervisor.models import (
    ComponentHealth,
    EnvironmentProbe,
    GatewayState,
    GatewayStatus,
    HealthReport,
    HealthState,
    IdaMcpConfig,
    IdeConfig,
    InstallationCheck,
)


def test_snapshot_to_form_state_maps_settings_fields() -> None:
    snapshot = SettingsSnapshot(
        ide_config=IdeConfig(
            language="zh",
            plugin_dir="E:/plugins",
            python_path="E:/Python/python.exe",
            request_timeout=45,
        ),
        ida_mcp_config=IdaMcpConfig(
            enable_stdio=True,
            wsl_path_bridge=True,
            http_host="127.0.0.1",
            http_port=2233,
            ida_default_port=10010,
            ida_host="127.0.0.2",
            ida_path="E:/IDA/ida64.exe",
            ida_python="E:/IDA/python.exe",
            open_in_ida_bundle_dir="E:/bundle",
            open_in_ida_autonomous=False,
            auto_start=True,
            server_name="IDA-MCP-Test",
            request_timeout=90,
            debug=True,
        ),
    )

    state = snapshot_to_form_state(snapshot)

    assert state.language == "zh"
    assert state.plugin_dir == "E:/plugins"
    assert state.ide_request_timeout == 45
    assert state.http_port == 2233
    assert state.wsl_path_bridge is True
    assert state.ida_default_port == 10010
    assert state.ida_host == "127.0.0.2"
    assert state.open_in_ida_bundle_dir == "E:/bundle"
    assert state.open_in_ida_autonomous is False
    assert state.auto_start is True
    assert state.server_name == "IDA-MCP-Test"
    assert state.ida_request_timeout == 90
    assert effective_install_python_path(snapshot) == "E:/Python/python.exe"


def test_form_state_to_updates_applies_defaults_and_cleans_values() -> None:
    state = SettingsFormState(
        python_path="  ",
        plugin_dir=" E:/plugins ",
        language="en",
        ide_request_timeout=30,
        enable_http=True,
        enable_stdio=False,
        enable_unsafe=True,
        wsl_path_bridge=True,
        http_host="   ",
        http_port=11338,
        http_path="   ",
        ida_default_port=10000,
        ida_host="   ",
        ida_path=" E:/IDA/ida64.exe ",
        ida_python=" E:/IDA/python.exe ",
        open_in_ida_bundle_dir=" E:/bundle ",
        open_in_ida_autonomous=False,
        auto_start=True,
        server_name="   ",
        ida_request_timeout=55,
        debug=False,
    )

    ide_updates, ida_mcp_updates = form_state_to_updates(state)

    assert ide_updates["python_path"] is None
    assert ide_updates["plugin_dir"] == "E:/plugins"
    assert ide_updates["request_timeout"] == 30
    assert ida_mcp_updates["http_host"] == "0.0.0.0"
    assert ida_mcp_updates["http_path"] == "/mcp"
    assert ida_mcp_updates["wsl_path_bridge"] is True
    assert ida_mcp_updates["ida_default_port"] == 10000
    assert ida_mcp_updates["ida_host"] == "127.0.0.1"
    assert ida_mcp_updates["ida_path"] == "E:/IDA/ida64.exe"
    assert ida_mcp_updates["open_in_ida_bundle_dir"] == "E:/bundle"
    assert ida_mcp_updates["open_in_ida_autonomous"] is False
    assert ida_mcp_updates["auto_start"] is True
    assert ida_mcp_updates["server_name"] == "IDA-MCP"
    assert ida_mcp_updates["request_timeout"] == 55


def test_build_check_message_keeps_summary_and_warning_lines() -> None:
    i18n = I18n("en")
    report = HealthReport(
        supervisor=ComponentHealth("supervisor", HealthState.OK, "Supervisor ready"),
        gateway=ComponentHealth("gateway", HealthState.WARNING, "Gateway stopped"),
        environment=ComponentHealth("environment", HealthState.OK, "Environment ready"),
        config=IdeConfig(),
        gateway_status=GatewayStatus(
            state=GatewayState.STOPPED,
            alive=False,
            proxy_alive=False,
            enabled=True,
            host="127.0.0.1",
            port=11338,
            path="/mcp",
        ),
        environment_probe=EnvironmentProbe(
            python_executable="python",
            python_version="3.12",
            ida_mcp_importable=True,
            ida_mcp_location="E:/DM/IDA-MCP",
        ),
    )
    installation = InstallationCheck(
        plugin_dir="E:/plugins",
        plugin_dir_exists=True,
        config_path="config.conf",
        config_exists=True,
        python_executable="python",
        python_exists=True,
        ida_mcp_py_exists=True,
        ida_mcp_package_exists=True,
        summary="Everything looks good",
        requirements_path="requirements.txt",
        requirements=["fastmcp", "pytest"],
        installed_requirements={"fastmcp": "1.0.0"},
        missing_requirements=["pytest"],
        warnings=["Check plugin dir permissions"],
    )

    message = build_check_message(
        report,
        installation,
        i18n.t,
        lambda value: (
            i18n.t("settings.bool.yes") if value else i18n.t("settings.bool.no")
        ),
    )

    assert message.summary == "Everything looks good"
    assert "Supervisor: ok - Supervisor ready" in message.details
    assert "Check plugin dir permissions" in message.details
    assert "requirements.txt: requirements.txt" in message.details
    assert "dependency status: 1/2 installed, 1 missing" in message.details
