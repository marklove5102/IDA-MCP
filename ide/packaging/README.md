# Packaging

本目录用于管理 IDE 的 **Nuitka** 打包与分发流程。

## 目标

- 将 `ide/` 编译为独立桌面应用
- 保持 `ida_mcp` 作为外部可管理组件
- 支持开发态与打包态统一路径解析

## 规划内容

- `build_nuitka.py`：跨平台共用的 Nuitka 构建参数入口
- `build_windows.ps1`：Windows 本地构建脚本
- 后续可补：Linux/macOS 构建脚本、图标、版本信息、安装器整合

## 当前依赖

建议在 IDE 虚拟环境中安装：

- `nuitka`
- `zstandard`

`zstandard` 对 onefile 模式尤其有用。

## 当前参数骨架

- `--standalone` / `--onefile`
- `--enable-plugin=pyside6`
- `--msvc=latest`
- `--windows-console-mode=disable`
- `--include-package=app`
- `--include-package=shared`
- `--include-package=supervisor`
- `--include-data-dir=app/assets=app/assets`（当 assets 非空时）
- `--windows-icon-from-ico=app.ico`（当图标存在时）

## 使用方式

先建议使用 standalone：

```powershell
.\packaging\build_windows.ps1 standalone
```

确认运行正常后，再尝试 onefile：

```powershell
.\packaging\build_windows.ps1 onefile
```

## 约束

- 不依赖仓库源码树运行
- 不依赖动态模块发现
- 资源路径必须通过运行时路径助手获取
