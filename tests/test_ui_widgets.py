#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI widgets 单元测试
测试增强的文件列表和日志组件
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ui.widgets.enhanced_file_list import EnhancedFileListWidget, FileItem
    from ui.widgets.enhanced_log_widget import EnhancedLogWidget, LogLevel
except ImportError:
    import pytest
    pytest.skip("PyQt6 未安装，跳过测试", allow_module_level=True)


class TestFileItem:
    """测试 FileItem 数据类"""

    def test_default_values(self):
        """测试默认值"""
        item = FileItem(path="/path/to/file.mp4")
        assert item.path == "/path/to/file.mp4"
        assert item.status == "待处理"
        assert item.progress == 0
        assert item.error is None

    def test_custom_values(self):
        """测试自定义值"""
        item = FileItem(
            path="/path/to/file.mp4",
            status="完成",
            progress=100,
            error=None
        )
        assert item.path == "/path/to/file.mp4"
        assert item.status == "完成"
        assert item.progress == 100

    def test_with_error(self):
        """测试带错误的情况"""
        item = FileItem(
            path="/path/to/file.mp4",
            status="错误",
            progress=50,
            error="文件不存在"
        )
        assert item.error == "文件不存在"


class TestEnhancedFileListWidget:
    """测试 EnhancedFileListWidget 类"""

    def test_initialization(self):
        """测试初始化"""
        widget = EnhancedFileListWidget()
        assert widget._files == []
        assert widget._is_dragging is False
        assert widget._drop_overlay is not None

    def test_add_single_file(self):
        """测试添加单个文件"""
        widget = EnhancedFileListWidget()
        widget.add_file("/path/to/file1.mp4")
        
        assert len(widget._files) == 1
        assert widget._files[0].path == "/path/to/file1.mp4"
        assert widget._files[0].status == "待处理"

    def test_add_multiple_files(self):
        """测试添加多个文件"""
        widget = EnhancedFileListWidget()
        files = [
            "/path/to/file1.mp4",
            "/path/to/file2.avi",
            "/path/to/file3.mkv"
        ]
        widget.add_files(files)
        
        assert len(widget._files) == 3

    def test_duplicate_file_not_added(self):
        """测试重复文件不会被添加"""
        widget = EnhancedFileListWidget()
        widget.add_file("/path/to/file.mp4")
        widget.add_file("/path/to/file.mp4")
        
        assert len(widget._files) == 1

    def test_get_files(self):
        """测试获取文件列表"""
        widget = EnhancedFileListWidget()
        widget.add_files(["/path/to/file1.mp4", "/path/to/file2.avi"])
        
        files = widget.get_files()
        assert len(files) == 2
        assert "/path/to/file1.mp4" in files
        assert "/path/to/file2.avi" in files

    def test_get_file_items(self):
        """测试获取文件项列表"""
        widget = EnhancedFileListWidget()
        widget.add_file("/path/to/file.mp4")
        
        items = widget.get_file_items()
        assert len(items) == 1
        assert isinstance(items[0], FileItem)

    def test_update_file_status(self):
        """测试更新文件状态"""
        widget = EnhancedFileListWidget()
        widget.add_file("/path/to/file.mp4")
        widget.update_file_status("/path/to/file.mp4", "完成", 100)
        
        assert widget._files[0].status == "完成"
        assert widget._files[0].progress == 100


class TestEnhancedLogWidget:
    """测试 EnhancedLogWidget 类"""

    def test_initialization(self):
        """测试初始化"""
        widget = EnhancedLogWidget()
        assert widget._logs == []
        assert widget._auto_scroll is True
        assert widget._current_filter == "ALL"
        assert widget._search_text == ""

    def test_log_info(self):
        """测试 INFO 级别日志"""
        widget = EnhancedLogWidget()
        widget.info("测试信息")
        
        assert len(widget._logs) == 1
        assert widget._logs[0]['level'] == LogLevel.INFO
        assert "测试信息" in widget._logs[0]['message']

    def test_log_debug(self):
        """测试 DEBUG 级别日志"""
        widget = EnhancedLogWidget()
        widget.debug("调试信息")
        
        assert len(widget._logs) == 1
        assert widget._logs[0]['level'] == LogLevel.DEBUG

    def test_log_warning(self):
        """测试 WARNING 级别日志"""
        widget = EnhancedLogWidget()
        widget.warning("警告信息")
        
        assert len(widget._logs) == 1
        assert widget._logs[0]['level'] == LogLevel.WARNING

    def test_log_error(self):
        """测试 ERROR 级别日志"""
        widget = EnhancedLogWidget()
        widget.error("错误信息")
        
        assert len(widget._logs) == 1
        assert widget._logs[0]['level'] == LogLevel.ERROR

    def test_log_success(self):
        """测试 SUCCESS 级别日志"""
        widget = EnhancedLogWidget()
        widget.success("成功信息")
        
        assert len(widget._logs) == 1
        assert widget._logs[0]['level'] == LogLevel.SUCCESS

    def test_multiple_logs(self):
        """测试多条日志"""
        widget = EnhancedLogWidget()
        widget.info("信息1")
        widget.debug("信息2")
        widget.warning("信息3")
        
        assert len(widget._logs) == 3

    def test_get_all_logs(self):
        """测试获取所有日志"""
        widget = EnhancedLogWidget()
        widget.info("信息1")
        widget.error("信息2")
        
        logs = widget.get_all_logs()
        assert len(logs) == 2
        assert isinstance(logs, list)

    def test_auto_scroll_default(self):
        """测试自动滚动默认开启"""
        widget = EnhancedLogWidget()
        assert widget._auto_scroll is True


class TestLogLevel:
    """测试 LogLevel 类"""

    def test_log_levels_exist(self):
        """测试所有日志级别存在"""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.SUCCESS == "SUCCESS"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
