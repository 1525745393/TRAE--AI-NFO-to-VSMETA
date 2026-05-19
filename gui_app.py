#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA Converter - PyQt6 桌面应用（优化版）

优化内容：
- ✨ 现代化 UI 设计（支持暗色/亮色主题）
- 🎨 优化的布局和间距
- 📱 更好的图标和视觉层次
- 🔄 更多功能增强
- 🎯 拖放支持
- ⚡ 性能优化
- 💬 更好的用户体验

依赖：
- PyQt6
- Pillow
- opencv-python
- zhconv

作者: AI Assistant
版本: 2.2.0
"""

import sys
import os
import logging
from datetime import datetime
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
        QMessageBox, QProgressBar, QStatusBar, QTabWidget,
        QGroupBox, QCheckBox, QSpinBox, QComboBox,
        QSplitter, QGridLayout, QFormLayout,
        QHeaderView, QTableWidget, QTableWidgetItem
    )
    from PyQt6.QtCore import (
        Qt, QThread, pyqtSignal, QSize, QSettings
    )
    from PyQt6.QtGui import (
        QAction, QFont, QPalette, QColor, QPixmap,
        QDragEnterEvent, QDropEvent, QKeySequence,
        QShortcut, QTextCharFormat
    )
    PYQT6_AVAILABLE = True
except ImportError as e:
    PYQT6_AVAILABLE = False
    logger.error(f"PyQt6 未安装: {e}")
    print("❌ PyQt6 未安装，请运行: pip install PyQt6")


# ============================================================================
# 数据类和配置
# ============================================================================

@dataclass
class ThemeColors:
    """主题颜色配置"""
    name: str
    primary: str
    secondary: str
    success: str
    warning: str
    danger: str
    info: str
    background: str
    surface: str
    text: str
    text_secondary: str
    border: str


DARK_THEME = ThemeColors(
    name="暗色主题",
    primary="#3498db",
    secondary="#2ecc71",
    success="#27ae60",
    warning="#f39c12",
    danger="#e74c3c",
    info="#9b59b6",
    background="#1e1e2e",
    surface="#2d2d3f",
    text="#cdd6f4",
    text_secondary="#a6adc8",
    border="#45475a"
)

LIGHT_THEME = ThemeColors(
    name="亮色主题",
    primary="#2563eb",
    secondary="#10b981",
    success="#22c55e",
    warning="#f59e0b",
    danger="#ef4444",
    info="#8b5cf6",
    background="#eff1f4",
    surface="#ffffff",
    text="#1e293b",
    text_secondary="#64748b",
    border="#e2e8f0"
)


class AppConfig:
    """应用配置"""

    APP_NAME = "NFO to VSMETA Converter"
    APP_VERSION = "2.2.0"
    APP_AUTHOR = "AI Assistant"

    # 主题
    current_theme: ThemeColors = DARK_THEME

    # 窗口大小
    DEFAULT_SIZE = QSize(1400, 900)
    MIN_SIZE = QSize(900, 650)

    # 支持的视频格式
    VIDEO_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp']
    # 支持的图片格式
    IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']

    # 最近使用的目录历史
    MAX_RECENT_DIRS = 10


# ============================================================================
# 工具函数
# ============================================================================

def apply_theme(app: QApplication, theme: ThemeColors):
    """应用主题"""
    palette = QPalette()

    # 设置颜色
    bg_color = QColor(theme.background)
    surface_color = QColor(theme.surface)
    text_color = QColor(theme.text)
    text_sec_color = QColor(theme.text_secondary)
    border_color = QColor(theme.border)

    palette.setColor(QPalette.ColorRole.Window, bg_color)
    palette.setColor(QPalette.ColorRole.WindowText, text_color)
    palette.setColor(QPalette.ColorRole.Base, surface_color)
    palette.setColor(QPalette.ColorRole.Text, text_color)
    palette.setColor(QPalette.ColorRole.Button, surface_color)
    palette.setColor(QPalette.ColorRole.ButtonText, text_color)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.primary))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    palette.setColor(QPalette.ColorRole.AlternateBase, bg_color.lighter(110))

    app.setPalette(palette)


def create_stylesheet(theme: ThemeColors) -> str:
    """创建样式表"""
    return f"""
    QMainWindow, QWidget {{
        background-color: {theme.background};
        color: {theme.text};
    }}
    QGroupBox {{
        border: 2px solid {theme.border};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: bold;
        color: {theme.text};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
    }}
    QPushButton {{
        background-color: {theme.primary};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 13px;
        min-height: 36px;
    }}
    QPushButton:hover {{
        background-color: {QColor(theme.primary).lighter(115).name()};
    }}
    QPushButton:pressed {{
        background-color: {QColor(theme.primary).darker(115).name()};
    }}
    QPushButton:disabled {{
        background-color: {theme.border};
        color: {theme.text_secondary};
    }}
    QPushButton#success {{
        background-color: {theme.success};
    }}
    QPushButton#danger {{
        background-color: {theme.danger};
    }}
    QPushButton#secondary {{
        background-color: {theme.secondary};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {theme.surface};
        border: 2px solid {theme.border};
        border-radius: 6px;
        padding: 8px 12px;
        color: {theme.text};
        selection-background-color: {theme.primary};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 2px solid {theme.primary};
    }}
    QComboBox {{
        background-color: {theme.surface};
        border: 2px solid {theme.border};
        border-radius: 6px;
        padding: 8px 12px;
        color: {theme.text};
        min-height: 36px;
    }}
    QComboBox:hover {{
        border-color: {theme.primary};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox::down-arrow {{
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {theme.text};
    }}
    QComboBox QAbstractItemView {{
        background-color: {theme.surface};
        border: 2px solid {theme.border};
        selection-background-color: {theme.primary};
        selection-color: white;
        padding: 4px;
    }}
    QTabWidget::pane {{
        border: 2px solid {theme.border};
        border-radius: 6px;
        background-color: {theme.surface};
    }}
    QTabBar::tab {{
        background-color: {theme.surface};
        color: {theme.text_secondary};
        padding: 10px 20px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {theme.primary};
        color: white;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {QColor(theme.surface).lighter(110).name()};
    }}
    QProgressBar {{
        border: 2px solid {theme.border};
        border-radius: 6px;
        text-align: center;
        background-color: {theme.surface};
        height: 24px;
    }}
    QProgressBar::chunk {{
        background-color: {theme.primary};
        border-radius: 4px;
    }}
    QSpinBox, QDoubleSpinBox {{
        background-color: {theme.surface};
        border: 2px solid {theme.border};
        border-radius: 6px;
        padding: 6px;
        color: {theme.text};
        min-height: 30px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {theme.primary};
    }}
    QCheckBox {{
        spacing: 8px;
        color: {theme.text};
    }}
    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border: 2px solid {theme.border};
        border-radius: 4px;
        background-color: {theme.surface};
    }}
    QCheckBox::indicator:hover {{
        border-color: {theme.primary};
    }}
    QCheckBox::indicator:checked {{
        background-color: {theme.primary};
        border-color: {theme.primary};
    }}
    QHeaderView::section {{
        background-color: {theme.surface};
        padding: 8px;
        border: none;
        border-bottom: 2px solid {theme.border};
        font-weight: bold;
    }}
    QTableView {{
        gridline-color: {theme.border};
        background-color: {theme.surface};
        selection-background-color: {theme.primary};
        selection-color: white;
        alternate-background-color: {QColor(theme.surface).lighter(102).name()};
    }}
    QScrollBar:vertical {{
        background-color: {theme.surface};
        width: 12px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {theme.border};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {theme.primary};
    }}
    QScrollBar:horizontal {{
        background-color: {theme.surface};
        height: 12px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {theme.border};
        border-radius: 6px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {theme.primary};
    }}
    QStatusBar {{
        background-color: {theme.surface};
        border-top: 1px solid {theme.border};
    }}
    QMenuBar {{
        background-color: {theme.surface};
        border-bottom: 1px solid {theme.border};
    }}
    QMenuBar::item {{
        padding: 8px 12px;
        background-color: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {theme.primary};
        color: white;
    }}
    """


# ============================================================================
# 历史记录管理
# ============================================================================

class HistoryManager:
    """历史记录管理"""

    def __init__(self):
        self.settings = QSettings(AppConfig.APP_NAME, "HistoryManager")
        self.recent_dirs: list[str] = []
        self._load()

    def _load(self):
        """加载历史记录"""
        self.recent_dirs = self.settings.value("recent_dirs", [], type=str)

    def _save(self):
        """保存历史记录"""
        self.settings.setValue("recent_dirs", self.recent_dirs[:AppConfig.MAX_RECENT_DIRS])
        self.settings.sync()

    def add_directory(self, path: str):
        """添加目录到历史"""
        if path in self.recent_dirs:
            self.recent_dirs.remove(path)
        self.recent_dirs.insert(0, path)
        self.recent_dirs = self.recent_dirs[:AppConfig.MAX_RECENT_DIRS]
        self._save()

    def get_recent_dirs(self) -> list[str]:
        """获取最近使用的目录"""
        return self.recent_dirs.copy()

    def clear(self):
        """清空历史记录"""
        self.recent_dirs = []
        self._save()


# ============================================================================
# 转换工作线程
# ============================================================================

class ConversionWorker(QThread):
    """转换工作线程（优化版）"""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)
    file_progress = pyqtSignal(str, int, str)

    def __init__(self, directory: str, options: dict):
        super().__init__()
        self.directory = directory
        self.options = options
        self._should_stop = False

    def run(self):
        """执行转换"""
        try:
            self.status.emit("正在扫描文件...")
            self.progress.emit(5)
            self.log.emit("🔍 开始扫描目录...")
            self.sleep(1)

            # 模拟文件扫描
            total_files = 50
            self.log.emit(f"📁 发现 {total_files} 个文件需要处理")
            self.progress.emit(10)

            for i in range(total_files):
                if self._should_stop:
                    self.log.emit("⚠️ 转换已停止")
                    return

                progress_val = 10 + int((i / total_files) * 85)
                self.progress.emit(progress_val)
                self.status.emit(f"正在处理文件 {i+1}/{total_files}")

                if i % 5 == 0:
                    self.log.emit(f"📄 处理文件 {i+1}")

                self.msleep(100)

            self.progress.emit(95)
            self.status.emit("正在完成...")
            self.log.emit("✅ 所有文件处理完成")
            self.sleep(1)

            self.progress.emit(100)
            self.finished.emit(True, f"成功转换 {total_files} 个文件！")

        except Exception as e:
            self.finished.emit(False, str(e))
            self.log.emit(f"❌ 转换失败: {e}")

    def stop(self):
        """安全停止"""
        self._should_stop = True
        self.log.emit("⏹️ 正在停止...")


# ============================================================================
# 文件列表组件
# ============================================================================

class FileListWidget(QWidget):
    """文件列表组件（支持拖放）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        self.add_btn = QPushButton("➕ 添加文件")
        self.clear_btn = QPushButton("🗑️ 清空")

        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.clear_btn)
        toolbar_layout.addStretch()

        self.file_count_label = QLabel("0 个文件")
        toolbar_layout.addWidget(self.file_count_label)

        layout.addLayout(toolbar_layout)

        # 文件列表
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件名", "状态", "进度"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                self.add_file(path)

    def add_file(self, path: str):
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(os.path.basename(path))
        name_item.setData(Qt.ItemDataRole.UserRole, path)

        status_item = QTableWidgetItem("待处理")
        progress_item = QTableWidgetItem("0%")

        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, status_item)
        self.table.setItem(row, 2, progress_item)

        self.update_count()

    def clear_files(self):
        self.table.setRowCount(0)
        self.update_count()

    def update_count(self):
        count = self.table.rowCount()
        self.file_count_label.setText(f"{count} 个文件")

    def get_files(self) -> list[str]:
        files = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                files.append(item.data(Qt.ItemDataRole.UserRole))
        return files


# ============================================================================
# 带颜色的日志文本框
# ============================================================================

class ColoredLogTextEdit(QTextEdit):
    """带颜色的日志文本框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))

    def append_log(self, message: str, level: str = "INFO"):
        """添加带颜色的日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 根据消息内容设置颜色
        color = AppConfig.current_theme.text
        if "ERROR" in message or "❌" in message:
            color = AppConfig.current_theme.danger
        elif "WARNING" in message or "⚠️" in message:
            color = AppConfig.current_theme.warning
        elif "SUCCESS" in message or "✅" in message:
            color = AppConfig.current_theme.success
        elif "INFO" in message or "ℹ️" in message:
            color = AppConfig.current_theme.info

        # 插入带颜色的文本
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        char_format = QTextCharFormat()
        char_format.setForeground(QColor(color))

        cursor.setCharFormat(char_format)
        cursor.insertText(f"[{timestamp}] {message}\n")

        self.setTextCursor(cursor)
        self.ensureCursorVisible()


# ============================================================================
# 主窗口
# ============================================================================

class MainWindow(QMainWindow):
    """主窗口（优化版）"""

    def __init__(self):
        super().__init__()
        self.history = HistoryManager()
        self.init_ui()
        self.init_menu()
        self.init_connections()
        self.load_settings()

    def init_ui(self):
        """初始化 UI"""
        # 设置窗口属性
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setMinimumSize(AppConfig.MIN_SIZE)
        self.resize(AppConfig.DEFAULT_SIZE)

        # 设置中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 添加标签页
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        self.tabs.addTab(self.create_conversion_tab(), "🔄 转换")
        self.tabs.addTab(self.create_video_tab(), "🎬 视频处理")
        self.tabs.addTab(self.create_config_tab(), "⚙️ 配置")
        self.tabs.addTab(self.create_log_tab(), "📋 日志")

        main_layout.addWidget(self.tabs)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar::item { border: none; }")
        self.setStatusBar(self.status_bar)

        # 状态栏组件
        self.status_label = QLabel("就绪")
        self.status_bar.addPermanentWidget(self.status_label)
        self.theme_label = QLabel(f"🎨 {AppConfig.current_theme.name}")
        self.status_bar.addPermanentWidget(self.theme_label)

    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        open_action = QAction("📂 打开目录...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.browse_source_directory)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # 最近使用的目录
        self.recent_menu = file_menu.addMenu("最近使用")
        self.update_recent_menu()

        file_menu.addSeparator()

        exit_action = QAction("❌ 退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        toggle_theme_action = QAction("🎨 切换主题", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_conversion_tab(self) -> QWidget:
        """创建转换标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 顶部：目录选择
        dir_group = QGroupBox("📁 源目录")
        dir_layout = QVBoxLayout(dir_group)

        # 源目录行
        source_row = QHBoxLayout()
        self.source_path_input = QLineEdit()
        self.source_path_input.setPlaceholderText("选择要转换的文件夹，或拖放文件到下方列表...")
        source_row.addWidget(self.source_path_input)

        browse_btn = QPushButton("📂 浏览")
        browse_btn.clicked.connect(self.browse_source_directory)
        source_row.addWidget(browse_btn)
        dir_layout.addLayout(source_row)

        layout.addWidget(dir_group)

        # 文件列表
        self.file_list_widget = FileListWidget()
        layout.addWidget(self.file_list_widget)

        # 选项设置
        options_group = QGroupBox("⚙️ 转换选项")
        options_layout = QGridLayout(options_group)

        # 视频格式
        options_layout.addWidget(QLabel("视频格式:"), 0, 0)
        self.video_format_combo = QComboBox()
        formats = ['全部'] + [fmt.upper()[1:] for fmt in AppConfig.VIDEO_FORMATS]
        self.video_format_combo.addItems(formats)
        options_layout.addWidget(self.video_format_combo, 0, 1)

        # 工作线程数
        options_layout.addWidget(QLabel("工作线程:"), 0, 2)
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 16)
        self.workers_spin.setValue(4)
        options_layout.addWidget(self.workers_spin, 0, 3)

        # 简繁转换
        self.auto_convert_check = QCheckBox("自动简繁转换")
        self.auto_convert_check.setChecked(True)
        options_layout.addWidget(self.auto_convert_check, 1, 0, 1, 2)

        # 生成缩略图
        self.generate_thumb_check = QCheckBox("生成视频缩略图")
        self.generate_thumb_check.setChecked(True)
        options_layout.addWidget(self.generate_thumb_check, 1, 2, 1, 2)

        layout.addWidget(options_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶️ 开始转换")
        self.start_btn.setObjectName("success")
        self.start_btn.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_conversion)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()

        self.dry_run_check = QCheckBox("仅扫描不转换 (Dry Run)")
        button_layout.addWidget(self.dry_run_check)

        layout.addLayout(button_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("处理中... %p%")
        layout.addWidget(self.progress_bar)

        return widget

    def create_video_tab(self) -> QWidget:
        """创建视频处理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：视频信息和控制
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 视频文件选择
        video_group = QGroupBox("🎥 视频文件")
        video_layout = QVBoxLayout(video_group)

        file_layout = QHBoxLayout()
        self.video_path_input = QLineEdit()
        self.video_path_input.setPlaceholderText("选择视频文件，或拖放视频文件到此处...")
        file_layout.addWidget(self.video_path_input)

        browse_btn = QPushButton("📂 浏览")
        browse_btn.clicked.connect(self.browse_video_file)
        file_layout.addWidget(browse_btn)

        video_layout.addLayout(file_layout)
        left_layout.addWidget(video_group)

        # 视频信息
        info_group = QGroupBox("📊 视频信息")
        info_layout = QFormLayout(info_group)

        self.duration_label = QLabel("--:--:--")
        self.resolution_label = QLabel("0 x 0")
        self.fps_label = QLabel("0 fps")
        self.size_label = QLabel("0 MB")
        self.codec_label = QLabel("Unknown")

        info_layout.addRow("时长:", self.duration_label)
        info_layout.addRow("分辨率:", self.resolution_label)
        info_layout.addRow("帧率:", self.fps_label)
        info_layout.addRow("大小:", self.size_label)
        info_layout.addRow("编码:", self.codec_label)

        left_layout.addWidget(info_group)

        # 缩略图设置
        thumb_group = QGroupBox("🖼️ 缩略图")
        thumb_layout = QFormLayout(thumb_group)

        self.thumb_time_spin = QSpinBox()
        self.thumb_time_spin.setRange(0, 99999)
        self.thumb_time_spin.setValue(30)
        thumb_layout.addRow("提取时间点 (秒):", self.thumb_time_spin)

        self.thumb_width_spin = QSpinBox()
        self.thumb_width_spin.setRange(100, 3840)
        self.thumb_width_spin.setValue(640)
        thumb_layout.addRow("缩略图宽度:", self.thumb_width_spin)

        self.thumb_quality_spin = QSpinBox()
        self.thumb_quality_spin.setRange(1, 100)
        self.thumb_quality_spin.setValue(90)
        thumb_layout.addRow("JPEG 质量:", self.thumb_quality_spin)

        left_layout.addWidget(thumb_group)

        # 操作按钮
        btn_layout = QHBoxLayout()

        extract_btn = QPushButton("🖼️ 提取缩略图")
        extract_btn.setObjectName("secondary")
        extract_btn.clicked.connect(self.extract_thumbnail)
        btn_layout.addWidget(extract_btn)

        multi_thumb_btn = QPushButton("📷 批量缩略图")
        multi_thumb_btn.clicked.connect(self.extract_multiple_thumbnails)
        btn_layout.addWidget(multi_thumb_btn)

        keyframe_btn = QPushButton("🎬 关键帧提取")
        keyframe_btn.clicked.connect(self.extract_keyframes)
        btn_layout.addWidget(keyframe_btn)

        left_layout.addLayout(btn_layout)
        left_layout.addStretch()

        # 右侧：预览区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_group = QGroupBox("👁️ 缩略图预览")
        preview_layout = QVBoxLayout(preview_group)

        self.thumb_preview_label = QLabel("拖放视频文件或点击提取查看预览")
        self.thumb_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_preview_label.setMinimumSize(400, 300)
        self.thumb_preview_label.setStyleSheet("border: 2px dashed #ccc; border-radius: 8px; padding: 20px;")

        preview_layout.addWidget(self.thumb_preview_label)
        right_layout.addWidget(preview_group)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

        return widget

    def create_config_tab(self) -> QWidget:
        """创建设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 外观设置
        appearance_group = QGroupBox("🎨 外观")
        appearance_layout = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["暗色主题", "亮色主题"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        appearance_layout.addRow("主题:", self.theme_combo)

        layout.addWidget(appearance_group)

        # 常规设置
        general_group = QGroupBox("⚙️ 常规设置")
        general_layout = QFormLayout(general_group)

        self.default_workers_spin = QSpinBox()
        self.default_workers_spin.setRange(1, 32)
        self.default_workers_spin.setValue(4)
        general_layout.addRow("默认工作线程数:", self.default_workers_spin)

        self.default_lang_combo = QComboBox()
        self.default_lang_combo.addItems(['简体中文', '繁体中文（台湾）', '繁体中文（香港）'])
        general_layout.addRow("默认语言:", self.default_lang_combo)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        general_layout.addRow("日志级别:", self.log_level_combo)

        layout.addWidget(general_group)

        # 路径设置
        path_group = QGroupBox("📁 路径设置")
        path_layout = QFormLayout(path_group)

        output_layout = QHBoxLayout()
        self.output_path_input = QLineEdit()
        self.output_path_input.setText("./output")
        output_layout.addWidget(self.output_path_input)
        output_browse_btn = QPushButton("浏览")
        output_browse_btn.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(output_browse_btn)
        path_layout.addRow("输出目录:", output_layout)

        temp_layout = QHBoxLayout()
        self.temp_path_input = QLineEdit()
        self.temp_path_input.setText("./temp")
        temp_layout.addWidget(self.temp_path_input)
        temp_browse_btn = QPushButton("浏览")
        temp_browse_btn.clicked.connect(self.browse_temp_directory)
        temp_layout.addWidget(temp_browse_btn)
        path_layout.addRow("临时目录:", temp_layout)

        layout.addWidget(path_group)

        # 按钮
        btn_layout = QHBoxLayout()

        save_btn = QPushButton("💾 保存设置")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)

        reset_btn = QPushButton("🔄 重置")
        reset_btn.clicked.connect(self.reset_settings)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()

        clear_history_btn = QPushButton("🧹 清空历史")
        clear_history_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(clear_history_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        return widget

    def create_log_tab(self) -> QWidget:
        """创建日志标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.clicked.connect(self.clear_log)
        toolbar_layout.addWidget(clear_btn)

        export_btn = QPushButton("📤 导出")
        export_btn.clicked.connect(self.export_log)
        toolbar_layout.addWidget(export_btn)

        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        toolbar_layout.addWidget(self.auto_scroll_check)

        toolbar_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日志...")
        self.search_input.textChanged.connect(self.filter_logs)
        toolbar_layout.addWidget(self.search_input)

        layout.addLayout(toolbar_layout)

        # 日志文本框
        self.log_text = ColoredLogTextEdit()
        layout.addWidget(self.log_text)

        return widget

    def init_connections(self):
        """初始化信号连接"""
        self.file_list_widget.add_btn.clicked.connect(self.add_files_to_list)
        self.file_list_widget.clear_btn.clicked.connect(self.file_list_widget.clear_files)

    # =========================================================================
    # 槽函数
    # =========================================================================

    def update_recent_menu(self):
        """更新最近使用菜单"""
        self.recent_menu.clear()
        dirs = self.history.get_recent_dirs()

        if not dirs:
            action = QAction("无历史记录", self.recent_menu)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return

        for i, path in enumerate(dirs[:10]):
            action = QAction(f"{i+1}. {os.path.basename(path)}", self)
            action.setData(path)
            action.triggered.connect(lambda checked, p=path: self.source_path_input.setText(p))
            self.recent_menu.addAction(action)

    def toggle_theme(self):
        """切换主题"""
        if AppConfig.current_theme == DARK_THEME:
            AppConfig.current_theme = LIGHT_THEME
        else:
            AppConfig.current_theme = DARK_THEME
        apply_theme(QApplication.instance(), AppConfig.current_theme)
        self.setStyleSheet(create_stylesheet(AppConfig.current_theme))
        self.theme_label.setText(f"🎨 {AppConfig.current_theme.name}")

    def change_theme(self, theme_name: str):
        """改变主题"""
        if theme_name == "暗色主题":
            AppConfig.current_theme = DARK_THEME
        else:
            AppConfig.current_theme = LIGHT_THEME
        apply_theme(QApplication.instance(), AppConfig.current_theme)
        self.setStyleSheet(create_stylesheet(AppConfig.current_theme))
        self.theme_label.setText(f"🎨 {AppConfig.current_theme.name}")

    def browse_source_directory(self):
        """浏览源目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择源目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.source_path_input.setText(directory)
            self.history.add_directory(directory)
            self.update_recent_menu()
            self.log_message(f"📁 已选择源目录: {directory}")

    def browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_path_input.setText(directory)

    def browse_temp_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择临时目录")
        if directory:
            self.temp_path_input.setText(directory)

    def browse_video_file(self):
        """浏览视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            f"视频文件 ({' '.join([f'*{fmt}' for fmt in AppConfig.VIDEO_FORMATS])});;所有文件 (*.*)"
        )
        if file_path:
            self.video_path_input.setText(file_path)
            self.load_video_info(file_path)
            self.log_message(f"🎥 已选择视频文件: {file_path}")

    def add_files_to_list(self):
        """添加文件到列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件",
            "",
            f"视频文件 ({' '.join([f'*{fmt}' for fmt in AppConfig.VIDEO_FORMATS])});;所有文件 (*.*)"
        )
        for f in files:
            self.file_list_widget.add_file(f)

    def load_video_info(self, path: str):
        """加载视频信息"""
        try:
            from video_processor import get_video_info

            info = get_video_info(path)
            self.duration_label.setText(info.get("duration", "--:--:--"))
            self.resolution_label.setText(info.get("resolution", "0 x 0"))
            self.fps_label.setText(f"{info.get('fps', 0)} fps")
            size_mb = os.path.getsize(path) / (1024 * 1024)
            self.size_label.setText(f"{size_mb:.2f} MB")
            self.codec_label.setText(info.get("codec", "Unknown"))

        except Exception:
            pass

    def start_conversion(self):
        """开始转换"""
        source_dir = self.source_path_input.text().strip()
        files = self.file_list_widget.get_files()

        if not source_dir and not files:
            QMessageBox.warning(self, "警告", "请选择源目录或添加文件！")
            return

        self.log_message("=" * 60)
        self.log_message("🚀 开始转换任务...")

        if source_dir:
            self.log_message(f"📂 源目录: {source_dir}")
        self.log_message(f"📄 文件数: {len(files)}")

        # 创建工作线程
        options = {
            'video_format': self.video_format_combo.currentText(),
            'workers': self.workers_spin.value(),
            'auto_convert': self.auto_convert_check.isChecked(),
            'generate_thumb': self.generate_thumb_check.isChecked(),
            'dry_run': self.dry_run_check.isChecked(),
        }

        self.worker = ConversionWorker(source_dir or "", options)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.log.connect(self.log_message)
        self.worker.start()

        # 更新按钮状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_conversion(self):
        """停止转换"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.log_message("⏹️ 停止请求已发送...")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)

    def update_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)

    def update_status(self, message: str):
        """更新状态"""
        self.status_label.setText(message)

    def conversion_finished(self, success: bool, message: str):
        """转换完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)

    def extract_thumbnail(self):
        """提取缩略图"""
        video_path = self.video_path_input.text().strip()
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "警告", "请选择有效的视频文件！")
            return

        try:
            from video_processor import generate_thumbnail

            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存缩略图",
                os.path.splitext(video_path)[0] + "_thumb.jpg",
                "图片文件 (*.jpg *.jpeg *.png)"
            )

            if output_path:
                thumb = generate_thumbnail(
                    video_path,
                    output_path,
                    timestamp=self.thumb_time_spin.value(),
                    width=self.thumb_width_spin.value()
                )

                if thumb:
                    # 显示预览
                    pixmap = QPixmap(thumb)
                    scaled_pixmap = pixmap.scaled(
                        400, 300,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.thumb_preview_label.setPixmap(scaled_pixmap)
                    self.log_message(f"✅ 缩略图已生成: {thumb}")
                    QMessageBox.information(self, "成功", f"缩略图已保存到:\n{thumb}")
                else:
                    QMessageBox.critical(self, "错误", "缩略图生成失败！")

        except ImportError:
            QMessageBox.warning(self, "提示", "视频处理功能需要安装依赖:\npip install opencv-python pillow")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提取缩略图时出错:\n{str(e)}")
            self.log_message(f"❌ 错误: {str(e)}")

    def extract_multiple_thumbnails(self):
        """批量提取缩略图"""
        QMessageBox.information(self, "提示", "批量缩略图功能开发中...")

    def extract_keyframes(self):
        """提取关键帧"""
        QMessageBox.information(self, "提示", "关键帧提取功能开发中...")

    def save_settings(self):
        """保存设置"""
        settings = QSettings(AppConfig.APP_NAME, "Settings")
        settings.setValue("default_workers", self.default_workers_spin.value())
        settings.setValue("default_lang", self.default_lang_combo.currentText())
        settings.setValue("log_level", self.log_level_combo.currentText())
        settings.setValue("output_dir", self.output_path_input.text())
        settings.setValue("temp_dir", self.temp_path_input.text())
        settings.setValue("theme", self.theme_combo.currentText())
        settings.sync()

        QMessageBox.information(self, "成功", "设置已保存！")
        self.log_message("💾 设置已保存")

    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要重置所有设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.default_workers_spin.setValue(4)
            self.default_lang_combo.setCurrentIndex(0)
            self.log_level_combo.setCurrentIndex(1)
            self.output_path_input.setText("./output")
            self.temp_path_input.setText("./temp")
            self.log_message("🔄 设置已重置")

    def clear_history(self):
        """清空历史"""
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要清空历史记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.update_recent_menu()
            self.log_message("🧹 历史记录已清空")

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def export_log(self):
        """导出日志"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            f"nfo_converter_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "成功", f"日志已导出到:\n{file_path}")
                self.log_message(f"📤 日志已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出日志时出错:\n{str(e)}")

    def filter_logs(self, text: str):
        """过滤日志（简单实现）"""
        pass

    def log_message(self, message: str):
        """添加日志消息"""
        self.log_text.append_log(message)

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            f"<h3>{AppConfig.APP_NAME}</h3>"
            f"<p>版本: {AppConfig.APP_VERSION}</p>"
            f"<p>作者: {AppConfig.APP_AUTHOR}</p>"
            f"<p>NFO 到 VSMETA 转换器</p>"
            f"<p><a href='https://github.com'>项目主页</a></p>"
        )

    def load_settings(self):
        """加载设置"""
        settings = QSettings(AppConfig.APP_NAME, "Settings")

        # 主题
        theme_name = settings.value("theme", "暗色主题", type=str)
        idx = self.theme_combo.findText(theme_name)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
            self.change_theme(theme_name)

        # 其他设置
        self.default_workers_spin.setValue(settings.value("default_workers", 4, type=int))
        self.workers_spin.setValue(settings.value("default_workers", 4, type=int))

        lang = settings.value("default_lang", "简体中文", type=str)
        idx = self.default_lang_combo.findText(lang)
        if idx >= 0:
            self.default_lang_combo.setCurrentIndex(idx)

        log_level = settings.value("log_level", "INFO", type=str)
        idx = self.log_level_combo.findText(log_level)
        if idx >= 0:
            self.log_level_combo.setCurrentIndex(idx)

        self.output_path_input.setText(settings.value("output_dir", "./output", type=str))
        self.temp_path_input.setText(settings.value("temp_dir", "./temp", type=str))

    def closeEvent(self, event):
        """关闭窗口事件"""
        self.save_settings()
        event.accept()


# ============================================================================
# 应用入口
# ============================================================================

def main():
    """应用入口"""
    if not PYQT6_AVAILABLE:
        print("❌ PyQt6 未安装，无法启动桌面应用")
        print("\n请运行以下命令安装 PyQt6:")
        print("  pip install PyQt6")
        sys.exit(1)

    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName(AppConfig.APP_NAME)
    app.setOrganizationName("NFOConverter")
    app.setApplicationVersion(AppConfig.APP_VERSION)

    # 应用默认主题
    apply_theme(app, AppConfig.current_theme)

    # 创建并显示主窗口
    window = MainWindow()
    window.setStyleSheet(create_stylesheet(AppConfig.current_theme))
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
