"""User-level JSON config store for the IDE MVP."""

from __future__ import annotations

import json
from pathlib import Path

from shared.paths import ensure_directory, get_ide_user_config_root

from .models import ConfigStoreInfo, IdeConfig


DEFAULT_CONFIG_FILENAME = "ide_config.json"


class IdeConfigStore:
    def __init__(self, config_path: Path | None = None) -> None:
        root = ensure_directory(get_ide_user_config_root())
        self._config_path = config_path or (root / DEFAULT_CONFIG_FILENAME)

    @property
    def config_path(self) -> Path:
        return self._config_path

    def info(self) -> ConfigStoreInfo:
        return ConfigStoreInfo(
            path=str(self._config_path), exists=self._config_path.exists()
        )

    def load(self) -> IdeConfig:
        if not self._config_path.exists():
            return IdeConfig()
        with self._config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return IdeConfig()
        return IdeConfig.from_dict(data)

    def save(self, config: IdeConfig) -> IdeConfig:
        ensure_directory(self._config_path.parent)
        with self._config_path.open("w", encoding="utf-8") as handle:
            json.dump(config.to_dict(), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return config

    def update(self, **updates: object) -> IdeConfig:
        current = self.load().to_dict()
        current.update(updates)
        return self.save(IdeConfig.from_dict(current))

    def reset(self) -> IdeConfig:
        config = IdeConfig()
        return self.save(config)
