"""
PyQt6 桌面应用测试
"""

import pytest
import sys
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 未安装")
class TestGuiApp:
    """GUI 应用测试"""

    @pytest.fixture
    def app(self):
        """创建 QApplication 实例"""
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        yield app
        # 不在这里退出，保持应用运行

    def test_app_import(self):
        """测试应用导入"""
        from gui_app import MainWindow, AppConfig
        assert MainWindow is not None
        assert AppConfig is not None

    def test_app_config(self):
        """测试应用配置"""
        from gui_app import AppConfig

        assert AppConfig.APP_NAME == "NFO to VSMETA Converter"
        assert AppConfig.APP_VERSION == "2.1.0"
        assert len(AppConfig.VIDEO_FORMATS) > 0
        assert len(AppConfig.IMAGE_FORMATS) > 0

    def test_main_window_creation(self, app):
        """测试主窗口创建"""
        from gui_app import MainWindow

        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "NFO to VSMETA Converter v2.1.0"

    def test_conversion_tab_exists(self, app):
        """测试转换标签页存在"""
        from gui_app import MainWindow

        window = MainWindow()
        # 检查标签页数量
        assert window.tabs.count() == 4  # 转换、视频、配置、日志

    def test_video_formats(self):
        """测试支持的视频格式"""
        from gui_app import AppConfig

        expected_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        for fmt in expected_formats:
            assert fmt in AppConfig.VIDEO_FORMATS


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 未安装")
class TestGuiFunctionality:
    """GUI 功能测试"""

    @pytest.fixture
    def app(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        yield app

    def test_conversion_worker_import(self):
        """测试转换工作线程导入"""
        from gui_app import ConversionWorker
        assert ConversionWorker is not None

    def test_browse_dialog(self, app):
        """测试浏览对话框"""
        from gui_app import MainWindow
        window = MainWindow()
        # 验证方法存在
        assert hasattr(window, 'browse_source_directory')
        assert hasattr(window, 'browse_video_file')

    def test_conversion_controls(self, app):
        """测试转换控制"""
        from gui_app import MainWindow
        window = MainWindow()

        # 验证控件存在
        assert hasattr(window, 'source_path_input')
        assert hasattr(window, 'video_format_combo')
        assert hasattr(window, 'workers_spin')
        assert hasattr(window, 'start_btn')
        assert hasattr(window, 'stop_btn')
        assert hasattr(window, 'progress_bar')


@pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 未安装")
class TestAppIntegration:
    """应用集成测试"""

    @pytest.fixture
    def app(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        yield app

    def test_video_processor_integration(self, app):
        """测试视频处理集成"""
        from gui_app import MainWindow
        window = MainWindow()

        # 验证视频处理控件存在
        assert hasattr(window, 'video_path_input')
        assert hasattr(window, 'thumb_time_spin')
        assert hasattr(window, 'thumb_width_spin')
        assert hasattr(window, 'thumb_preview_label')

    def test_log_system(self, app):
        """测试日志系统"""
        from gui_app import MainWindow
        window = MainWindow()

        assert hasattr(window, 'log_text')
        assert hasattr(window, 'log_message')
        assert hasattr(window, 'clear_log')
        assert hasattr(window, 'export_log')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
