"""IDA 生命周期管理 - 启动与关闭。"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Annotated, Optional, Any, List

try:
    from pydantic import Field
except ImportError:
    Field = lambda **kwargs: None  # type: ignore

# 导入配置
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import get_ida_path

# 导入 forward
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)
from _state import forward  # type: ignore

def _wsl_to_win_path(path: str) -> str:
    """Convert WSL path to Windows path if running in WSL."""
    if not os.path.exists("/proc/version"):
        return path
        
    try:
        with open("/proc/version", "r") as f:
            if "microsoft" not in f.read().lower():
                return path
    except Exception:
        return path
        
    try:
        # 使用 wslpath 转换路径
        result = subprocess.check_output(["wslpath", "-w", path], stderr=subprocess.DEVNULL)
        return result.decode().strip()
    except Exception:
        return path

def register_tools(server: Any) -> None:
    """注册生命周期工具到服务器。"""
    
    @server.tool(description="Launch IDA Pro with the specified file. Automatically attempts to load IDA-MCP plugin.")
    def open_in_ida(
        file_path: Annotated[str, Field(description="Path to the file to open (executable or IDB)")],
        ida_path: Annotated[Optional[str], Field(description="Path to ida.exe. Defaults to configured path.")] = None,
        extra_args: Annotated[Optional[List[str]], Field(description="Extra arguments to pass to IDA")] = None,
    ) -> dict:
        """Open a file in IDA Pro."""
        try:
            # 1. 确定 IDA 路径
            target_ida = ida_path or get_ida_path()
            if not target_ida:
                return {"error": "IDA path not configured. Please set IDA_PATH environment variable or 'ida_path' in config.conf."}
            
            # WSL 适配：get_ida_path() 可能会返回 WSL 路径 (e.g. /mnt/c/...)
            # 但我们需要调用 Windows 程序，所以如果是在 WSL 下，且路径是 /mnt/c/... 格式，
            # 我们需要将其转回 Windows 格式 (C:\...) 才能被 Windows 的 interop 机制正确调用
            # 或者我们直接使用 WSL 路径，依赖 WSL 的 interop 机制（它通常能处理 /mnt/c/Program Files/...）
            
            # 经过验证，WSL interop 可以直接执行 /mnt/c/Path/To/ida.exe
            # 但 subprocess.Popen 在 WSL 下检查可执行权限时可能会有问题
            # 所以我们还是检查一下是否存在
            
            if not os.path.exists(target_ida):
                return {"error": f"IDA executable not found at: {target_ida}"}
                
            # 2. 确定目标文件
            if not os.path.exists(file_path):
                 return {"error": f"File not found: {file_path}"}
            
            # WSL 路径适配: 如果在 WSL 环境下，需要将文件路径转换为 Windows 路径
            # 注意: target_ida 已经是 Windows 路径（因为我们要在 WSL 调 win 程序）
            # 但 file_path 可能是 WSL 路径 (/mnt/c/...)，需要转换
            final_file_path = _wsl_to_win_path(os.path.abspath(file_path))
                 
            # 如果是在 WSL 环境中，我们需要将 WSL 路径 (/mnt/c/...) 转换为 Windows 路径 (C:\...) 
            # 否则 Windows 的 ida.exe 无法正确识别自身路径（如果通过 args 传入）
            # 但 subprocess.Popen 第一个参数如果是 /mnt/c/...，WSL interop 会自动处理。
            
            # 3. 构造命令
            # 假设 IDA-MCP 插件已安装在 plugins 目录，直接启动即可。
            # 如果 target_ida 是 WSL 路径 (/mnt/c/...)，它将被 WSL interop 转换为 Windows 路径执行
            cmd = [target_ida]
            launch_args = list(extra_args or [])
            # 默认使用 autonomous mode，尽量压掉打开文件时的交互确认对话框。
            if not any(arg.upper() == "-A" for arg in launch_args):
                launch_args.insert(0, "-A")
            if launch_args:
                cmd.extend(launch_args)
                
            cmd.append(final_file_path)
            
            # 4. 启动进程
            # 设置环境变量 IDA_MCP_AUTO_START=1 以自动启动插件
            env = os.environ.copy()
            env["IDA_MCP_AUTO_START"] = "1"
            
            # 使用 Popen 启动并不等待
            # WSL 兼容:
            # 1. 如果在 WSL 且 target_ida 是 exe, interop 会处理 (前提是 interop.enabled=true)
            # 2. 我们已经转换了文件路径为 Windows 格式
            # 3. cwd 设为 IDA 所在目录的父目录可能更好，或者直接继承当前目录（如果不重要）
            # 注意: 在 WSL 下 dirname(target_ida) 可能得到 Windows 格式路径 (e.g. C:\...), 
            # 这作为 cwd 传给 subprocess (即 Linux syscall) 会失败。
            # 所以在 WSL 下我们不指定 cwd，或者必须转换为 /mnt/c/... 格式。
            # Windows 程序对 CWD 敏感，我们尝试转换 target_ida 的目录为 WSL 路径
            
            cwd = os.path.dirname(target_ida)
            # 如果是在 WSL 下，target_ida 已经是 WSL 路径 (由 get_ida_path 处理)，所以 cwd 也是 WSL 路径，直接使用即可。
            # 但如果用户传入的是 Windows 路径，我们需要处理。
            
            if os.path.exists("/proc/version"):
                try:
                    with open("/proc/version", "r") as f:
                        if "microsoft" in f.read().lower():
                             # 如果 cwd 是 Windows 路径 (C:\...)，需要转换为 WSL 路径
                             if ":" in cwd and "\\" in cwd:
                                 try:
                                     wsl_cwd = subprocess.check_output(["wslpath", "-u", cwd], stderr=subprocess.DEVNULL).decode().strip()
                                     cwd = wsl_cwd
                                 except Exception:
                                     cwd = None
                except Exception:
                    pass
            
            subprocess.Popen(cmd, cwd=cwd, env=env, close_fds=True if sys.platform != 'win32' else False)
            return {"status": "ok", "message": f"Launched IDA: {' '.join(cmd)}"}
        except Exception as e:
            return {"error": f"Failed to launch IDA: {e}"}

    @server.tool(description="Close the target IDA instance. Warning: This terminates the process.")
    def close_ida(
        save: Annotated[bool, Field(description="Whether to save IDB file before closing")] = True,
        port: Annotated[Optional[int], Field(description="Instance port override")] = None,
        timeout: Annotated[Optional[int], Field(description="Timeout in seconds")] = None,
    ) -> dict:
        """Close IDA Pro instance."""
        # 优先使用 forward 转发到 IDA 内部执行，因为这需要调用 IDA API
        # 且需要确保在正确的实例上下文中执行
        return forward("close_ida", {"save": save}, port, timeout=timeout)
