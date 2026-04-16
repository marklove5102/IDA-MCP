# IDA-MCP Repository Roadmap Index

仓库现已拆分为多个主要子项目，各自维护独立的规划文档：

- `ida_mcp/roadmap.md`：`ida-mcp` 核心能力层 roadmap
- `ide/roadmap.md`：PySide6 桌面 IDE roadmap

## 子项目定位

### `ida_mcp/`

负责：

- IDA 插件入口
- MCP / HTTP proxy / gateway
- 多实例生命周期管理
- 分析、修改、建模、资源与控制能力

### `ide/`

负责：

- PySide6 桌面 IDE
- Supervisor / 安装与状态检查
- 多 Agent 审计工作台
- SQLite 持久化、事件流、checkpoint、文件查看与编辑

## 阅读顺序

1. 先看 `project.md` 了解仓库级项目地图
2. 看 `ida_mcp/project.md` 与 `ida_mcp/roadmap.md` 理解核心能力层
3. 看 `ide/project.md` 与 `ide/roadmap.md` 理解桌面 IDE 规划
