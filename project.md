# IDA-MCP Repository Project Map

## 仓库结构

```text
IDA-MCP/
├── ide/                          # PySide6 桌面 IDE（主项目）
│   ├── project.md                # IDE 结构与项目地图
│   ├── roadmap.md                # IDE 产品与工程规划
│   ├── launcher.py               # IDE 启动入口
│   ├── app/                      # UI 层（PySide6）
│   │   ├── ui/                   # 页面与控件
│   │   ├── presenters/           # 展示层逻辑
│   │   ├── services/             # 业务服务
│   │   └── i18n.py               # 中英双语国际化
│   ├── supervisor/               # 安装、配置、gateway 管理
│   │   ├── models.py             # 数据模型（IdeConfig、IdaMcpConfig）
│   │   ├── manager.py            # Supervisor 统一管理器
│   │   ├── gateway_controller.py # Gateway 启停控制
│   │   ├── install_runner.py     # 安装执行器
│   │   └── config_store.py       # IDE 配置持久化
│   ├── shared/                   # 共享工具
│   │   ├── ida_mcp_config.py     # ida_mcp config.conf 读写
│   │   └── paths.py              # 路径辅助函数
│   ├── resources/
│   │   └── ida_mcp/              # ida_mcp 受管资源（安装源）
│   │       ├── ida_mcp.py        # IDA 插件入口
│   │       ├── ida_mcp/          # IDA 插件包
│   │       │   ├── command.py    # CLI 入口（gateway start 等）
│   │       │   ├── config.py     # 配置加载器
│   │       │   ├── control.py    # Gateway 控制封装
│   │       │   ├── registry.py   # 多实例注册与 gateway 启动
│   │       │   ├── registry_server.py  # 独立 gateway 服务器
│   │       │   ├── api_*.py      # MCP 工具实现
│   │       │   └── proxy/        # stdio/HTTP MCP proxy
│   │       └── requirements.txt  # IDA Python 依赖
│   ├── tests/                    # pytest 测试
│   └── packaging/                # Nuitka 打包
├── test/                         # 旧测试（兼容）
├── skills/                       # MCP skill 文档
├── API.md                        # 工具与响应契约参考
├── project.md                    # 本文件
├── roadmap.md                    # Roadmap 索引
├── README.md                     # 英文用户文档
└── README_CN.md                  # 中文用户文档
```

## 子项目职责

### `ide/` — 产品与编排层

- PySide6 桌面 IDE（安装、配置、状态监控、工作区）
- Supervisor 管理 gateway 生命周期（启动、停止、健康检查）
- 多 Agent 审计工作台（规划中）
- `ida_mcp` 作为受管资源，IDE 不在代码层面 import 它

### `ide/resources/ida_mcp/` — IDA 插件资源

- 由 IDE 安装到 IDA 的 `plugins/` 目录
- 运行在 IDA Python 环境中，依赖 IDA SDK
- 提供 MCP 工具、gateway 服务器、多实例管理

## 文档入口

| 文档 | 说明 |
|------|------|
| `ide/project.md` | IDE 子项目详细结构 |
| `ide/roadmap.md` | IDE 产品与工程规划 |
| `ide/rules.md` | IDE 编码边界规则 |
| `API.md` | MCP 工具 API 参考 |
