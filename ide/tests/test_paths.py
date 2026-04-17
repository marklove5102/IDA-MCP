from pathlib import Path

from shared.paths import (
    get_build_root,
    get_ida_mcp_resources_dir,
    get_ide_user_config_root,
    get_logs_root,
    get_nuitka_output_root,
    get_packaging_root,
    get_project_root,
    get_resources_root,
    get_workspaces_root,
)


def test_runtime_path_helpers_resolve_inside_ide_project() -> None:
    project_root = get_project_root()

    assert project_root.name == "ide"
    assert get_resources_root() == project_root / "resources"
    assert get_logs_root() == project_root / "logs"
    assert get_workspaces_root() == project_root / "workspaces"
    assert get_build_root() == project_root / "build"
    assert get_nuitka_output_root() == project_root / "build" / "nuitka"
    assert get_packaging_root() == project_root / "packaging"


def test_ida_mcp_resources_dir_contains_required_files() -> None:
    resources_dir = get_ida_mcp_resources_dir()

    assert resources_dir.name == "ida_mcp"
    assert (resources_dir / "ida_mcp.py").exists()
    assert (resources_dir / "ida_mcp").is_dir()
    assert (resources_dir / "requirements.txt").exists()
    assert (resources_dir / "ida_mcp" / "command.py").exists()


def test_ide_user_config_root_is_nested_under_app_config_root(monkeypatch) -> None:
    appdata = Path("C:/Users/test/AppData/Roaming")
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)

    assert get_ide_user_config_root() == appdata / "ida-mcp" / "ide"
