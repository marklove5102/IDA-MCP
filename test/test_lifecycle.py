"""测试生命周期管理工具 (open_in_ida, close_ida)。

注意：这些测试涉及启动和关闭进程，可能会影响正在运行的 IDA 实例。
建议在受控环境中运行。
"""
import pytest
import os
import time
import subprocess
import sys
from unittest.mock import MagicMock, patch

# 添加项目根目录到 sys.path 以便导入 ida_mcp 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ida_mcp.proxy.proxy_lifecycle import _wsl_to_win_path

pytestmark = pytest.mark.lifecycle


class TestLifecycleOpen:
    """Lifecycle management tests - Open IDA.
    Runs first to initialize environment.
    """

    def test_open_in_ida_launch(self, tool_caller):
        """Test launching IDA."""
        # Use project sample file
        sample_path = os.path.join(PROJECT_ROOT, "test", "samples", "complex.exe")
        
        # Ensure file exists
        if not os.path.exists(sample_path):
            pytest.skip(f"Sample file not found: {sample_path}")
            
        print(f"\nAttempting to launch IDA with: {sample_path}")
        result = tool_caller("open_in_ida", {"file_path": sample_path})
        
        # Check launch status
        if "error" in result:
            error_msg = result["error"]
            if "not configured" in error_msg or "executable not found" in error_msg:
                pytest.skip(f"IDA environment not configured: {error_msg}")
            else:
                pytest.fail(f"Failed to launch IDA: {error_msg}")
        
        assert "status" in result
        assert result["status"] == "ok"
        assert "Launched IDA" in result["message"]

        # Wait for IDA to be ready
        print("\nWaiting for IDA to initialize...")
        max_retries = 30
        for i in range(max_retries):
            try:
                # Try to list instances to see if our instance registered
                instances = tool_caller("list_instances", {})
                if isinstance(instances, list) and len(instances) > 0:
                    print(f"IDA instance found after {i+1} retries.")
                    # Wait a bit more for full initialization
                    time.sleep(5)
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
             print("Warning: IDA instance did not register in time. Subsequent tests might fail.")


class TestLifecycleErrors:
    """生命周期管理测试 - 异常情况。"""

    def test_open_in_ida_invalid_path(self, tool_caller):
        """测试打开不存在的文件。"""
        result = tool_caller("open_in_ida", {"file_path": "non_existent_file.exe"})
        assert "error" in result
        # Since we fixed proxy_lifecycle.py, we expect a proper error message, not 500
        assert "not found" in result["error"] or "File not found" in result["error"]


    def test_open_in_ida_no_config(self, tool_caller):
        """测试未配置 IDA 路径的情况（模拟）。"""
        # 我们尝试传递一个不存在的 ida_path 来触发错误
        result = tool_caller("open_in_ida", {
            "file_path": __file__,  # 使用当前文件作为目标
            "ida_path": "Z:/non_existent/ida.exe"
        })
        assert "error" in result
        assert "not found" in result["error"] or "executable" in result["error"] or "Failed to launch" in result["error"]

    def test_open_in_ida_tool_exists(self, tool_caller):
        """验证 open_in_ida 工具已注册。"""
        result = tool_caller("open_in_ida", {"file_path": "invalid", "ida_path": "invalid"})
        assert "error" in result
        assert "not found" in result["error"] or "executable" in result["error"] or "Failed to launch" in result["error"]


    def test_wsl_path_conversion(self):
        """测试 WSL 路径转换逻辑 (单元测试)。"""
        
        # Mock os.path.exists 和 open 来模拟 WSL 环境
        with patch("os.path.exists") as mock_exists:
            # 需要正确处理多次调用 os.path.exists
            # 第一次检查 /proc/version (True)，第二次检查 /proc/version (True)
            def side_effect(path):
                if path == "/proc/version":
                    return True
                return False
            mock_exists.side_effect = side_effect
            
            with patch("builtins.open", new_callable=MagicMock) as mock_open:
                # 模拟读取 /proc/version 内容
                mock_file = MagicMock()
                mock_file.read.return_value = "Linux version ... Microsoft ..."
                mock_open.return_value.__enter__.return_value = mock_file
                
                # Mock subprocess.check_output
                with patch("subprocess.check_output") as mock_sub:
                    mock_sub.return_value = b"C:\\test\n"
                    
                    # 测试转换
                    result = _wsl_to_win_path("/mnt/c/test")
                    assert result == "C:\\test"
                    
                    # 验证调用参数
                    mock_sub.assert_called_with(["wslpath", "-w", "/mnt/c/test"], stderr=subprocess.DEVNULL)

    def test_wsl_path_conversion_non_wsl(self):
        """测试非 WSL 环境下的路径转换 (单元测试)。"""
        with patch("os.path.exists") as mock_exists:
            # 模拟 /proc/version 不存在
            mock_exists.return_value = False
            assert _wsl_to_win_path("/home/user/test") == "/home/user/test"


class TestLifecycleClose:
    """Lifecycle management tests - Close IDA.
    Runs last to clean up environment.
    """

    def test_close_ida(self, tool_caller):
        """Test closing IDA (runs last)."""
        # This will actually close IDA!
        print("\nAttempting to close IDA...")
        result = tool_caller("close_ida", {"save": False})
        
        if "error" in result:
             # If no instance is running, that's fine for this test context if we just want to clean up
             # But if we expected it to run, maybe we should warn
             print(f"Close IDA result: {result}")
        else:
             assert "status" in result
             assert result["status"] == "ok"
             
        # Wait a bit for process cleanup
        time.sleep(2)
