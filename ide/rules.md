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

## 5. `ida_mcp` 边界

- `ide/` 不直接把 `ida_mcp/` 当内部源码模块耦合使用
- `ida_mcp` 是外部被管理组件
- 对 `ida_mcp` 的配置、安装、检查、启动停止应通过 `supervisor/` 管理

## 6. 打包约束

- 目标分发方式为 Nuitka
- 避免动态导入与隐式插件发现
- 路径统一通过 `shared/runtime.py` 与 `shared/paths.py` 获取
- 不假设运行时仍然存在仓库源码树
