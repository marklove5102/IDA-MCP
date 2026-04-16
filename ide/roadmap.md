# IDE Roadmap

## 子项目定位

`ide/` 是一个基于 **PySide6** 的跨平台桌面 IDE，用于承载 IDA-MCP 的多 Agent 审计工作台，以及 `ida_mcp` 的安装、配置、启动、停止与状态检查。

它不是 Web 子项目，也不安装到 IDA plugin 目录。

---

## 核心目标

### 1. 作为桌面工作台

- 左上显示审计 plan 进度
- 左下显示 IDA 状态、当前文件与模式
- 中间提供 Agent 群聊天区
- 右侧展示 workspace、文件树和 artifacts
- 侧边栏提供 `Chat` / `Files` / `Settings` / `Status`

### 2. 作为 ida_mcp 控制中心

- 探测 Python 和 IDA 环境
- 安装和修复 `ida_mcp`
- 启动/停止 gateway
- 启动/关闭 IDA
- 管理配置 profile
- 提供健康检查与状态聚合

### 3. 作为审计运行环境

- 管理 workspace
- 使用 SQLite 持久化 run / plan / thread / message / artifact / checkpoint
- 接入 LangGraph + DeepAgents
- 支持恢复、人工介入和报告导出

---

## 技术路线

- UI：`PySide6`
- Supervisor：Python 本地后台进程
- Persistence：`SQLite`
- Orchestration：`LangGraph + DeepAgents`
- 底层能力：`ida_mcp`
- 分发：`Nuitka`

---

## 推荐进程模型

```text
PySide6 IDE UI
  <-> Supervisor
        |- ida_mcp gateway
        |- IDA instance A
        |- IDA instance B
```

原则：

- UI 不直接管理复杂进程
- Supervisor 是唯一控制面
- `ida_mcp` 继续作为底层能力层

---

## 阶段规划

## P0：方向切换与骨架落地

- 建立 `ide/` 子项目文档
- 建立 `app/`、`supervisor/`、`shared/`、`bootstrap/` 骨架
- 明确 `ida_mcp` 与 `ide` 的边界

## P1：Supervisor MVP

- Python 环境探测
- IDA 路径探测
- `ida_mcp` 安装检查
- gateway 启动/停止/状态
- IDA 启动/关闭/状态

## P2：PySide6 最小 IDE 壳

- 主窗口
- Sidebar：Chat / Files / Settings / Status
- Status 页面
- Settings 页面
- IDA 状态面板

## P3：工作台主体

- Plan 面板
- Chat 面板
- Workspace 面板
- Files 双模式查看器（text / hex）

## P4：审计运行与多 Agent

- workspace + SQLite
- run / plan / thread / message / artifact / checkpoint
- LangGraph + DeepAgents 编排
- 人工介入与恢复

## P5：产品化

- 基于 Nuitka 的打包与分发
- 平台适配（Windows / Linux / macOS）
- 安装修复和日志诊断

## Nuitka 约束

- IDE 运行时不能依赖上级仓库源码结构
- 避免动态导入、反射式页面发现和隐式插件系统
- 资源路径必须统一走运行时路径助手
- `ida_mcp` 作为外部组件由 IDE 托管，不与 IDE 一起静态内嵌为源码依赖
- 打包脚本、参数与平台差异处理统一收敛到 `ide/packaging/`

---

## 明确不做的方向

- 不再使用 Web / React 作为主路线
- 不把 IDE 安装进 IDA plugin 目录
- 不让 UI 直接耦合 `ida_mcp` 内部实现
- 不把完整通用 IDE 作为第一阶段目标
