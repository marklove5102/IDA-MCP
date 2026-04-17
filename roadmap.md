# IDA-MCP Repository Roadmap Index

仓库以 `ide/` 子项目为主体，`ida_mcp` 作为受管资源打包在 `ide/resources/` 中。

## 子项目

### `ide/` — 主项目

PySide6 桌面 IDE，负责安装、配置、状态监控和 gateway 生命周期管理。

规划文档：`ide/roadmap.md`

### `ide/resources/ida_mcp/` — 受管资源

IDA 插件源码（`ida_mcp.py` + `ida_mcp/` 包），安装时由 IDE 复制到 IDA plugins 目录。包含 `command.py` CLI 和 `registry_server.py` gateway 服务器。

规划文档：`ide/resources/ida_mcp/ida_mcp/roadmap.md`

## 阅读顺序

1. `project.md` — 仓库级项目地图
2. `ide/project.md` + `ide/roadmap.md` — IDE 子项目结构与规划
3. `README.md` — 用户文档
