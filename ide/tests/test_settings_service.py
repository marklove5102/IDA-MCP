from dataclasses import dataclass

from app.services.settings_service import SettingsService
from supervisor.models import IdaMcpConfig, IdeConfig


@dataclass
class _StubClient:
    ide_config: IdeConfig
    ida_mcp_config: IdaMcpConfig

    def __post_init__(self) -> None:
        self.ide_updates: list[dict[str, object]] = []
        self.ida_updates: list[dict[str, object]] = []

    def get_ide_config(self) -> IdeConfig:
        return self.ide_config

    def get_ida_mcp_config(self) -> IdaMcpConfig:
        return self.ida_mcp_config

    def update_ide_config(self, **updates: object) -> IdeConfig:
        self.ide_updates.append(updates)
        for key, value in updates.items():
            setattr(self.ide_config, key, value)
        return self.ide_config

    def update_ida_mcp_config(self, **updates: object) -> IdaMcpConfig:
        self.ida_updates.append(updates)
        for key, value in updates.items():
            setattr(self.ida_mcp_config, key, value)
        return self.ida_mcp_config


def test_settings_service_normalizes_language_without_rewriting_boundaries() -> None:
    client = _StubClient(
        ide_config=IdeConfig(language="ZH"),
        ida_mcp_config=IdaMcpConfig(ida_python="C:/IDA/python.exe"),
    )

    snapshot = SettingsService(client).load()

    assert snapshot.ide_config.language == "zh"
    assert snapshot.ide_config.plugin_dir  # has default IDA plugins path


def test_settings_service_saves_normalized_updates() -> None:
    client = _StubClient(
        ide_config=IdeConfig(language="en"),
        ida_mcp_config=IdaMcpConfig(),
    )

    SettingsService(client).save(
        ide_updates={"plugin_dir": "C:/plugins", "language": "ZH"},
        ida_mcp_updates={"ida_path": "C:/IDA/ida64.exe", "debug": True},
    )

    assert client.ide_updates[-1]["language"] == "zh"
    assert client.ide_updates[-1]["plugin_dir"] == "C:/plugins"
    assert client.ida_updates[-1]["ida_path"] == "C:/IDA/ida64.exe"
