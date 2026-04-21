# IDE Rules

## 1. UI 与逻辑边界

`app/ui/` 只负责：

- PySide6 widgets 与布局
- signal / slot
- QFileDialog / QMessageBox 等 Qt 交互
- 将 view model 渲染到控件上

`app/ui/` 不应承载：

- 配置模型与表单更新映射
- 安装检查/重装结果的文案拼装
- `SupervisorSnapshot` 到状态卡/树结构的展示模型转换
- 与 `ida_mcp` 或 supervisor 相关的业务判断

这些逻辑应放在：

- `app/services/`：应用服务、保存/检查/安装调用
- `app/presenters/`：snapshot/form state 到 UI 展示模型的转换
- `supervisor/`：配置、安装、状态、gateway 控制

## 2. Presenter 规则

Presenter 应尽量是：

- 纯 Python
- dataclass + 小函数
- 不依赖 Qt 控件
- 可直接单测

## 3. SettingsPage 规则

- `SettingsPage` 只负责读取控件值、写回控件值、触发 dialog
- 表单到 updates 的映射放到 `app/presenters/settings_presenter.py`
- check / install / reinstall 的结果文本拼装放到 presenter 或 service

## 4. MainWindow 规则

- `MainWindow` 只负责页面切换、状态渲染、菜单与交互
- `SupervisorSnapshot` 到 status cards / tree rows 的转换放到 `app/presenters/main_window_presenter.py`

## 5. `ida_mcp` 与 IDE 完全隔离

### 5.1 核心原则：两个独立运行时

`ida_mcp` 和 IDE 运行在**完全不同的 Python 环境中**：

- **`ida_mcp`** 安装到 IDA 的 `plugins/` 目录，运行在 IDA 内置的 `ida-python` 环境中。
- **IDE** 是独立的 Nuitka 二进制分发，运行在自己的 Python 环境中。

因此 **IDE 代码不得 `import ida_mcp`**，反之亦然。两者之间**零代码级依赖**。

### 5.2 通信方式

IDE 与 `ida_mcp` 只能通过以下方式交互：

- **Gateway HTTP API**（`/internal/call`, `/internal/instances` 等）
- **MCP 协议**（通过 FastMCP Client 连接 proxy）
- **文件系统**（安装时复制文件，写入 `config.conf`）

### 5.3 依赖方向（零依赖）

```
┌─────────────┐               ┌──────────────┐
│ ida_mcp.py  │───→ ida_mcp/  │    ide/      │
│ (插件壳)     │    (自包含)    │  (IDE 应用)  │
└─────────────┘               └──────────────┘
    ✗ 无 import 关系 ✗

通信方式: HTTP API / MCP 协议 / 文件系统（config.conf）
```

```python
# ✗ 禁止 — IDE 代码导入 ida_mcp
# 在 ide/app/ 或 ide/supervisor/ 中：
from ida_mcp import config          # ✗ 不同 Python 环境
import ida_mcp                      # ✗ 打包后不存在

# ✗ 禁止 — ida_mcp 代码导入 IDE 或外部模块
# 在 ida_mcp/ 包内：
from app.services import something  # ✗
import ida_mcp_top_level            # ✗ 顶层 ida_mcp.py

# ✓ 允许 — IDE 通过 HTTP/MCP 与 ida_mcp 通信
# 在 supervisor/ 中：
result = http_post("http://127.0.0.1:11338/internal/call", {...})

# ✓ 允许 — IDE 通过文件系统管理 ida_mcp
# 在 install_runner.py 中：
shutil.copy2(source, target)  # 复制插件文件
config_path.write_text(...)   # 写入 config.conf
```

### 5.4 `ida_mcp/` 自包含约束

`ida_mcp/`（`ide/resources/ida_mcp/ida_mcp/`）会被完整复制到 IDA `plugins/` 目录：

- **不得导入任何外部模块**（ide/ 下的代码、项目根目录文件）
- **可以导入**标准库、第三方包（fastmcp, starlette, uvicorn）、IDA SDK
- `plugin_runtime.py` 通过回调注入避免直接依赖 IDA SDK

### 5.5 IDE 资源管理

`ide/resources/ida_mcp/` 仅作为**安装源**——IDE 将其中的文件复制到 IDA plugins 目录，不做 import。

## 6. 用户数据目录

### 6.1 目录位置

所有持久化用户数据统一存放在 IDE 安装目录内的 `data/` 子目录中，完全自包含、可移动：

```
{IDE安装目录}/
├── ida-mcp-ide.exe
├── resources/
└── data/                       ← 用户数据目录，更新时不得删除
    ├── ide.db                  # IDE 配置数据库 (SQLite)
    └── skills/                 # 已安装的 MCP 技能包
        └── {skill_name}/       # 每个技能一个目录
```

开发模式下为 `{ide}/data/`，打包模式下为 `{exe所在目录}/data/`。

### 6.2 生存期保证

**用户数据目录在更新/重装时不得被删除。** 具体规则：

- `ide.db`：IDE 全局配置，更新时保留
- `skills/`：已安装技能，更新时保留
- 安装器（`install_runner.py`）只操作 IDA `plugins/` 目录，不触碰 `data/` 目录

### 6.3 路径获取

所有路径统一通过 `shared/paths.py` 获取：

| 函数 | 返回值 | 用途 |
|------|--------|------|
| `get_data_root()` | `{exe_dir}/data/` | 用户数据根目录 |
| `get_ide_user_config_root()` | `{exe_dir}/data/` | 同上（兼容旧调用） |
| `get_skills_dir()` | `{exe_dir}/data/skills/` | 技能安装目录 |
| `get_ida_mcp_resources_dir()` | `{exe_dir}/resources/ida_mcp/` | ida_mcp 安装源（只读） |

## 7. 打包约束

- 目标分发方式为 Nuitka
- 避免动态导入与隐式插件发现
- 路径统一通过 `shared/runtime.py` 与 `shared/paths.py` 获取
- 不假设运行时仍然存在仓库源码树
- `ida_mcp/` 不随 IDE 二进制一起编译，仅作为资源文件复制
