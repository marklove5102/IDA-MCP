import sys
from pathlib import Path

from supervisor.installer import EnvironmentInstaller


def test_check_installation_reports_missing_config(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ida_mcp.py").write_text("# plugin\n", encoding="utf-8")
    (plugin_dir / "ida_mcp").mkdir()
    python_path = Path(sys.executable)
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    installer = EnvironmentInstaller(repo_root=tmp_path)
    result = installer.check_installation(
        plugin_dir=plugin_dir,
        python_executable=python_path,
    )

    assert result.plugin_dir == str(plugin_dir)
    assert result.config_exists is False
    assert result.ida_mcp_py_exists is True
    assert result.ida_mcp_package_exists is True
    assert result.python_exists is True
    assert result.requirements == ["pytest"]
    assert result.requirements_path == str(tmp_path / "requirements.txt")
    assert "pytest" in result.installed_requirements
    assert result.missing_requirements == []


def test_check_installation_reports_missing_requirements(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ida_mcp.py").write_text("# plugin\n", encoding="utf-8")
    (plugin_dir / "ida_mcp").mkdir()
    (tmp_path / "requirements.txt").write_text(
        "definitely-not-installed-package-xyz==1.0\n",
        encoding="utf-8",
    )

    installer = EnvironmentInstaller(repo_root=tmp_path)
    result = installer.check_installation(
        plugin_dir=plugin_dir,
        python_executable=Path(sys.executable),
    )

    assert result.installed_requirements == {}
    assert result.missing_requirements == ["definitely-not-installed-package-xyz==1.0"]


def test_check_installation_uses_repo_root_requirements(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ida_mcp.py").write_text("# plugin\n", encoding="utf-8")
    (plugin_dir / "ida_mcp").mkdir()

    repo_requirements = tmp_path / "requirements.txt"
    repo_requirements.write_text("pytest\n", encoding="utf-8")

    installer = EnvironmentInstaller(repo_root=tmp_path)
    result = installer.check_installation(
        plugin_dir=plugin_dir,
        python_executable=Path(sys.executable),
    )

    assert result.requirements == ["pytest"]
    assert result.requirements_path == str(repo_requirements)


def test_repair_config_copies_default_template(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ida_mcp.py").write_text("# plugin\n", encoding="utf-8")
    (plugin_dir / "ida_mcp").mkdir()
    default_config = tmp_path / "ida_mcp" / "config.conf"
    default_config.parent.mkdir()
    default_config.write_text("enable_http = true\n", encoding="utf-8")

    installer = EnvironmentInstaller(repo_root=tmp_path)
    result = installer.repair_config(plugin_dir=plugin_dir)

    assert result.ok is True
    assert result.created is True
    assert (plugin_dir / "ida_mcp" / "config.conf").read_text(
        encoding="utf-8"
    ) == "enable_http = true\n"


def test_reinstall_reports_existing_config(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ida_mcp.py").write_text("# plugin\n", encoding="utf-8")
    (plugin_dir / "ida_mcp").mkdir()
    (plugin_dir / "ida_mcp" / "config.conf").write_text(
        "debug = false\n", encoding="utf-8"
    )
    default_config = tmp_path / "ida_mcp" / "config.conf"
    default_config.parent.mkdir()
    default_config.write_text("enable_http = true\n", encoding="utf-8")

    installer = EnvironmentInstaller(repo_root=tmp_path)
    result = installer.reinstall(plugin_dir=plugin_dir)

    assert result.ok is True
    assert result.already_exists is True
    assert result.created is False


def test_repair_config_uses_explicit_config_path(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "ida_mcp.py").write_text("# plugin\n", encoding="utf-8")
    (plugin_dir / "ida_mcp").mkdir()
    default_config = tmp_path / "ida_mcp" / "config.conf"
    default_config.parent.mkdir()
    default_config.write_text("enable_http = true\n", encoding="utf-8")
    explicit_config = tmp_path / "custom" / "config.conf"

    installer = EnvironmentInstaller(repo_root=tmp_path)
    result = installer.repair_config(plugin_dir=plugin_dir, config_path=explicit_config)

    assert result.ok is True
    assert result.created is True
    assert result.config_path == str(explicit_config)
    assert explicit_config.read_text(encoding="utf-8") == "enable_http = true\n"
