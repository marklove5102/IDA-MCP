# IDE

`ide/` 是 IDA-MCP 的 PySide6 桌面 IDE 子项目。

它不是 Web 前端，也不是 IDA 插件；它是独立分发的桌面工作台，用来：

- 安装、配置、启动、停止、检查 `ida_mcp`
- 提供多 Agent 审计工作台
- 提供 Chat / Files / Settings / Status 界面
- 管理 workspace、SQLite、事件流、checkpoint 和文件查看

## 子项目结构

```text
ide/
├── README.md
├── roadmap.md
├── project.md
├── launcher.py
├── bootstrap/
├── app/
├── packaging/
├── supervisor/
├── shared/
└── tests/
```

## 核心分层

- `app/`：PySide6 UI 与应用装配
- `packaging/`：Nuitka 打包脚本、分发配置与平台说明
- `supervisor/`：安装、配置、进程管理、状态聚合
- `shared/`：共享 DTO、事件、枚举、路径工具
- `bootstrap/`：IDA 启动桥接脚本

## 目标

- 独立桌面分发
- 不依赖 Web/React
- 不安装到 IDA plugin 目录
- 通过 supervisor 托管 `ida_mcp`

## 打包约束

后续桌面分发目标是 **Nuitka**。

因此当前实现遵守以下约束：

- IDE 自身不依赖仓库源码树才能运行
- `ida_mcp` 被视为外部被管理组件，而不是 IDE 内部包
- 少用动态导入与隐式模块发现
- 资源与运行时路径统一通过 `shared/paths.py` / `shared/runtime.py` 管理
- 打包脚本与平台说明放在 `packaging/`
