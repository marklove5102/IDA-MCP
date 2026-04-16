from pathlib import Path

from shared.paths import (
    get_assets_root,
    get_build_root,
    get_ide_user_config_root,
    get_logs_root,
    get_nuitka_output_root,
    get_packaging_root,
    get_project_root,
    get_repo_root,
    get_workspaces_root,
)


def test_runtime_path_helpers_resolve_inside_ide_project() -> None:
    project_root = get_project_root()

    assert project_root.name == "ide"
    assert get_assets_root() == project_root / "app" / "assets"
    assert get_logs_root() == project_root / "logs"
    assert get_workspaces_root() == project_root / "workspaces"
    assert get_build_root() == project_root / "build"
    assert get_nuitka_output_root() == project_root / "build" / "nuitka"
    assert get_packaging_root() == project_root / "packaging"


def test_repo_root_detects_monorepo_parent() -> None:
    repo_root = get_repo_root()

    assert repo_root.name == "IDA-MCP"
    assert (repo_root / "ida_mcp.py").exists()
    assert (repo_root / "ida_mcp").exists()


def test_ide_user_config_root_is_nested_under_app_config_root(monkeypatch) -> None:
    appdata = Path("C:/Users/test/AppData/Roaming")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert get_ide_user_config_root() == appdata / "ida-mcp" / "ide"
