# IDA-MCP Repository Project Map

本文件只描述仓库级边界；各子项目的详细结构与规划已拆分到各自目录。

## 仓库结构

```text
IDA-MCP/
├── ida_mcp.py                  # IDA 插件入口
├── command.py                  # CLI 入口
├── install.py                  # 安装与配置脚本
├── ida_mcp/                    # 核心能力层子项目
│   ├── project.md
│   └── roadmap.md
├── ide/                        # PySide6 桌面 IDE 子项目
│   ├── project.md
│   ├── roadmap.md
│   ├── app/
│   └── supervisor/
├── test/                       # pytest 测试
├── README.md
├── README_CN.md
└── API.md
```

## 子项目职责

### `ida_mcp/`

核心能力层：

- IDA 实例内 MCP 服务
- Gateway / Registry / Proxy
- Tool / Resource / Control
- 生命周期与实例路由

### `ide/`

产品与编排层：

- Workspace / AuditRun / Thread / Artifact / Checkpoint
- LangGraph + DeepAgents 审计编排
- PySide6 UI、Supervisor、事件流与工作台

## 文档入口

- `ida_mcp/project.md`：核心层目录树与模块地图
- `ida_mcp/roadmap.md`：核心层后续规划
- `ide/project.md`：IDE 子项目结构、目录树、项目地图
- `ide/roadmap.md`：IDE 子项目产品与工程规划
