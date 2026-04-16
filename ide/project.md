# IDE Project Map

## 子项目定位

`ide/` 是基于 PySide6 的桌面 IDE 子项目，负责：

- 桌面工作台 UI
- Supervisor 后台控制面
- `ida_mcp` 安装、配置、启动、停止和状态检查
- workspace、运行状态和文件查看

---

## 目录树

```text
ide/
├── README.md
├── roadmap.md
├── project.md
├── launcher.py
├── bootstrap/
│   ├── ida_bootstrap.py
│   └── env_bootstrap.py
├── app/
│   ├── main.py
│   ├── wiring.py
│   ├── state/
│   │   ├── app_state.py
│   │   ├── session_state.py
│   │   └── models.py
│   ├── services/
│   │   ├── supervisor_client.py
│   │   ├── workspace_service.py
│   │   ├── file_preview_service.py
│   │   └── settings_service.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── docks/
│   │   │   ├── plan_panel.py
│   │   │   ├── ida_status_panel.py
│   │   │   ├── workspace_panel.py
│   │   │   └── sidebar_panel.py
│   │   ├── chat/
│   │   ├── files/
│   │   └── settings/
│   └── assets/
├── packaging/
│   ├── build_nuitka.py
│   ├── build_windows.ps1
│   └── README.md
├── supervisor/
│   ├── main.py
│   ├── api.py
│   ├── manager.py
│   ├── process_store.py
│   ├── health.py
│   ├── installer.py
│   ├── config_store.py
│   ├── ida_launcher.py
│   ├── gateway_controller.py
│   └── models.py
├── shared/
│   ├── dto.py
│   ├── events.py
│   ├── enums.py
│   ├── paths.py
│   └── runtime.py
└── tests/
```

---

## 模块地图

### `launcher.py`

桌面 IDE 启动入口。

### `bootstrap/`

提供给 IDA 启动链使用的桥接脚本。

### `app/`

PySide6 应用层。

#### `app/state/`
- 应用状态
- 当前会话状态
- 视图模型

#### `app/services/`
- UI 对 supervisor 的调用客户端
- workspace 和文件预览服务
- settings 读写

#### `app/ui/`
- 主窗口
- 各 dock / panel
- Chat、Files、Settings 界面

### `supervisor/`

IDE 的后台控制面。

- `installer.py`：安装、修复、探测
- `config_store.py`：IDE 配置 profile
- `gateway_controller.py`：管理 gateway
- `ida_launcher.py`：管理 IDA 启动与关闭
- `health.py`：聚合状态与健康检查
- `manager.py`：统一调度

### `shared/`

共享 DTO、事件、枚举、路径工具。

### `packaging/`

Nuitka 打包脚本、构建参数与平台分发说明。

---

## UI 布局映射

### Sidebar

- `Chat`
- `Files`
- `Settings`
- `Status`

### Left Top

- `PlanPanel`

### Left Bottom

- `IdaStatusPanel`

### Center

- `ChatPanel`

### Right

- `WorkspacePanel`

### Files

- `TextView`
- `HexView`

---

## 与 ida_mcp 的边界

`ide/` 不实现 IDA 底层能力。

`ide/` 通过 supervisor 使用 `ida_mcp` 提供的：

- gateway / registry
- tool / resource
- lifecycle / open_in_ida
- status / control

`ida_mcp/` 不承载 IDE 的 workspace、plan、chat、settings、status UI 等产品状态。

---

## Nuitka 运行时约束

- `ide/` 必须能在开发态与 Nuitka 打包态都正确解析资源与运行目录
- 运行时代码不能假设仓库根目录始终存在
- `shared/runtime.py` 负责统一判断当前是否为打包态
- `shared/paths.py` 负责返回用户配置目录、运行目录、资源目录、打包输出目录等路径
