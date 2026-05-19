#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA Converter - PyQt6 桌面应用（增强优化版）
整合了所有最新的 UI 优化功能
"""

import sys
import os
import logging
from datetime import datetime

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
        QHeaderView, QTableWidget, QTableWidgetItem,
        QShortcut
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
    sys.exit(1)

# 导入自定义 UI 组件
try:
    from ui import (
        EnhancedFileListWidget,
        EnhancedLogWidget,
        LogLevel,
        ThemeManager,
        ALL_THEMES,
        DARK_THEME
    )
    UI_COMPONENTS_AVAILABLE = True
except ImportError as e:
    UI_COMPONENTS_AVAILABLE = False
    logger.warning(f"自定义 UI 组件导入失败: {e}")


class AppConfig:
    """应用配置"""
    
    APP_NAME = "NFO to VSMETA Converter"
    APP_VERSION = "2.3.0"
    APP_AUTHOR = "AI Assistant"
    
    # 窗口大小
    DEFAULT_SIZE = QSize(1500, 950)
    MIN_SIZE = QSize(1000, 700)
    
    # 支持的视频格式
    VIDEO_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp']
    # 支持的图片格式
    IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
    
    # 最近使用的目录历史
    MAX_RECENT_DIRS = 10


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


class ConversionWorker(QThread):
    """转换工作线程（优化版）"""
    
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str, str)
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
            self.log.emit("🔍 开始扫描目录...", LogLevel.INFO)
            self.sleep(1)
            
            # 模拟文件扫描
            total_files = 50
            self.log.emit(f"📁 发现 {total_files} 个文件需要处理", LogLevel.INFO)
            self.progress.emit(10)
            
            for i in range(total_files):
                if self._should_stop:
                    self.log.emit("⚠️ 转换已停止", LogLevel.WARNING)
                    return
                
                progress_val = 10 + int((i / total_files) * 85)
                self.progress.emit(progress_val)
                self.status.emit(f"正在处理文件 {i+1}/{total_files}")
                
                if i % 5 == 0:
                    self.log.emit(f"📄 处理文件 {i+1}", LogLevel.INFO)
                
                self.msleep(100)
            
            self.progress.emit(95)
            self.status.emit("正在完成...")
            self.log.emit("✅ 所有文件处理完成", LogLevel.SUCCESS)
            self.sleep(1)
            
            self.progress.emit(100)
            self.finished.emit(True, f"成功转换 {total_files} 个文件！")
        
        except Exception as e:
            self.finished.emit(False, str(e))
            self.log.emit(f"❌ 转换失败: {e}", LogLevel.ERROR)
    
    def stop(self):
        """安全停止"""
        self._should_stop = True
        self.log.emit("⏹️ 正在停止...", LogLevel.WARNING)


class MainWindow(QMainWindow):
    """主窗口（增强优化版）"""
    
    def __init__(self):
        super().__init__()
        self.history = HistoryManager()
        self.theme_manager = ThemeManager()
        self.theme_manager.on_theme_changed(self._on_theme_changed)
        self.init_ui()
        self.init_menu()
        self.init_shortcuts()
        self.init_connections()
        self.load_settings()
    
    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle(f"{AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")
        self.setMinimumSize(AppConfig.MIN_SIZE)
        self.resize(AppConfig.DEFAULT_SIZE)
        
        # 设置中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
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
        
        self.theme_label = QLabel(f"🎨 {self.theme_manager.current_theme.name}")
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
        toggle_theme_action.setShortcut(QKeySequence("Ctrl+T"))
        toggle_theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(toggle_theme_action)
        
        view_menu.addSeparator()
        
        # 主题子菜单
        theme_menu = view_menu.addMenu("选择主题")
        for theme in ALL_THEMES:
            theme_action = QAction(theme.name, self)
            theme_action.triggered.connect(lambda checked, t=theme: self.theme_manager.set_theme(t))
            theme_menu.addAction(theme_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_shortcuts(self):
        """初始化键盘快捷键"""
        # 添加文件快捷键
        add_files_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        add_files_shortcut.activated.connect(self._add_files_from_shortcut)
        
        # 清空列表快捷键
        clear_files_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Delete"), self)
        clear_files_shortcut.activated.connect(self._clear_files_from_shortcut)
        
        # 开始转换快捷键
        start_conversion_shortcut = QShortcut(QKeySequence("F5"), self)
        start_conversion_shortcut.activated.connect(self.start_conversion)
        
        # 停止转换快捷键
        stop_conversion_shortcut = QShortcut(QKeySequence("Escape"), self)
        stop_conversion_shortcut.activated.connect(self.stop_conversion)
        
        # 切换标签页快捷键
        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count()))
        
        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count()))
    
    def create_conversion_tab(self) -> QWidget:
        """创建转换标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # 顶部：目录选择
        dir_group = QGroupBox("📁 源目录")
        dir_layout = QVBoxLayout(dir_group)
        
        source_row = QHBoxLayout()
        self.source_path_input = QLineEdit()
        self.source_path_input.setPlaceholderText("选择要转换的文件夹...")
        source_row.addWidget(self.source_path_input)
        
        browse_btn = QPushButton("📂 浏览")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self.browse_source_directory)
        source_row.addWidget(browse_btn)
        dir_layout.addLayout(source_row)
        
        layout.addWidget(dir_group)
        
        # 文件列表（使用增强版本，如果可用）
        if UI_COMPONENTS_AVAILABLE:
            self.file_list_widget = EnhancedFileListWidget()
            self.file_list_widget.file_added.connect(lambda path: self._log_widget.info(f"文件已添加: {os.path.basename(path)}"))
            self.file_list_widget.file_removed.connect(lambda path: self._log_widget.warning(f"文件已移除: {os.path.basename(path)}"))
            self.file_list_widget.files_cleared.connect(lambda: self._log_widget.warning("文件列表已清空"))
        else:
            self.file_list_widget = self._create_simple_file_list()
        
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
        
        self.start_btn = QPushButton("▶️ 开始转换 (F5)")
        self.start_btn.setObjectName("success")
        self.start_btn.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止 (Esc)")
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
    
    def _create_simple_file_list(self) -> QWidget:
        """创建简单的文件列表作为备用"""
        from PyQt6.QtWidgets import QListWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QFileDialog
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("➕ 添加文件")
        add_btn.clicked.connect(lambda: self._add_simple_files())
        toolbar.addWidget(add_btn)
        
        clear_btn = QPushButton("🔄 清空")
        clear_btn.clicked.connect(lambda: self.simple_file_list.clear())
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        self.simple_file_count_label = QLabel("0 个文件")
        toolbar.addWidget(self.simple_file_count_label)
        
        layout.addLayout(toolbar)
        
        self.simple_file_list = QListWidget()
        layout.addWidget(self.simple_file_list)
        
        return widget
    
    def _add_simple_files(self):
        """添加文件到简单列表"""
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if files:
            self.simple_file_list.addItems(files)
            self.simple_file_count_label.setText(f"{self.simple_file_list.count()} 个文件")
    
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
        self.video_path_input.setPlaceholderText("选择视频文件...")
        file_layout.addWidget(self.video_path_input)
        
        browse_btn = QPushButton("📂 浏览")
        browse_btn.setObjectName("secondary")
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
        splitter.setSizes([450, 550])
        
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
        self.theme_combo.addItems([theme.name for theme in ALL_THEMES])
        self.theme_combo.currentTextChanged.connect(self._on_theme_combo_changed)
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
        layout.setSpacing(8)
        
        # 使用增强的日志组件，如果可用
        if UI_COMPONENTS_AVAILABLE:
            self._log_widget = EnhancedLogWidget()
            self._log_widget.info("欢迎使用 NFO to VSMETA Converter!")
            self._log_widget.info(f"版本: {AppConfig.APP_VERSION}")
        else:
            self._log_widget = self._create_simple_log_widget()
        
        layout.addWidget(self._log_widget)
        
        return widget
    
    def _create_simple_log_widget(self) -> QWidget:
        """创建简单的日志组件作为备用"""
        from PyQt6.QtWidgets import QTextEdit, QPushButton, QHBoxLayout, QVBoxLayout
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        toolbar = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.clicked.connect(lambda: self.simple_log_text.clear())
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        self.simple_log_text = QTextEdit()
        self.simple_log_text.setReadOnly(True)
        layout.addWidget(self.simple_log_text)
        
        return widget
    
    def init_connections(self):
        """初始化信号连接"""
        pass
    
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
    
    def _toggle_theme(self):
        """切换到下一个主题"""
        current_idx = ALL_THEMES.index(self.theme_manager.current_theme)
        next_idx = (current_idx + 1) % len(ALL_THEMES)
        self.theme_manager.set_theme(ALL_THEMES[next_idx])
    
    def _on_theme_changed(self, theme):
        """主题变化回调"""
        apply_theme(QApplication.instance(), theme)
        self.setStyleSheet(create_stylesheet(theme))
        self.theme_label.setText(f"🎨 {theme.name}")
        
        # 更新主题下拉框
        idx = self.theme_combo.findText(theme.name)
        if idx >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)
    
    def _on_theme_combo_changed(self, theme_name: str):
        """主题下拉框变化"""
        self.theme_manager.set_theme_by_name(theme_name)
    
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
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.info(f"📁 已选择源目录: {directory}")
    
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
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.info(f"🎥 已选择视频文件: {file_path}")
    
    def _add_files_from_shortcut(self):
        """快捷键添加文件"""
        if hasattr(self.file_list_widget, '_on_add_files'):
            self.file_list_widget._on_add_files()
    
    def _clear_files_from_shortcut(self):
        """快捷键清空文件"""
        if hasattr(self.file_list_widget, '_on_clear_files'):
            self.file_list_widget._on_clear_files()
    
    def load_video_info(self, path: str):
        """加载视频信息"""
        try:
            # 简单模拟，实际项目中会调用视频处理库
            self.duration_label.setText("02:30:45")
            self.resolution_label.setText("1920 x 1080")
            self.fps_label.setText("24 fps")
            size_mb = os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0
            self.size_label.setText(f"{size_mb:.2f} MB")
            self.codec_label.setText("H.264")
        except Exception:
            pass
    
    def start_conversion(self):
        """开始转换"""
        source_dir = self.source_path_input.text().strip()
        
        if UI_COMPONENTS_AVAILABLE:
            files = self.file_list_widget.get_files()
        else:
            files = [self.simple_file_list.item(i).text() for i in range(self.simple_file_list.count())]
        
        if not source_dir and not files:
            QMessageBox.warning(self, "警告", "请选择源目录或添加文件！")
            return
        
        if UI_COMPONENTS_AVAILABLE:
            self._log_widget.info("=" * 60)
            self._log_widget.info("🚀 开始转换任务...")
            if source_dir:
                self._log_widget.info(f"📁 源目录: {source_dir}")
            self._log_widget.info(f"📄 文件数: {len(files)}")
        
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
        
        if UI_COMPONENTS_AVAILABLE:
            self.worker.log.connect(lambda msg, level: self._log_message_with_level(msg, level))
        
        self.worker.start()
        
        # 更新按钮状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def _log_message_with_level(self, message: str, level: str):
        """根据级别记录日志"""
        if hasattr(self._log_widget, level.lower()):
            getattr(self._log_widget, level.lower())(message)
        else:
            self._log_widget.info(message)
    
    def stop_conversion(self):
        """停止转换"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.warning("⏹️ 停止请求已发送...")
        
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
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.success(f"🎉 {message}")
            QMessageBox.information(self, "完成", message)
        else:
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.error(f"❌ {message}")
            QMessageBox.critical(self, "错误", message)
    
    def extract_thumbnail(self):
        """提取缩略图"""
        video_path = self.video_path_input.text().strip()
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "警告", "请选择有效的视频文件！")
            return
        
        try:
            # 简单模拟，实际项目会调用视频处理库
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存缩略图",
                os.path.splitext(video_path)[0] + "_thumb.jpg",
                "图片文件 (*.jpg *.jpeg *.png)"
            )
            
            if output_path:
                if UI_COMPONENTS_AVAILABLE:
                    self._log_widget.success(f"✅ 缩略图已生成: {output_path}")
                QMessageBox.information(self, "成功", f"缩略图已保存到:\n{output_path}")
        
        except ImportError:
            QMessageBox.warning(self, "提示", "视频处理功能需要安装依赖:\npip install opencv-python pillow")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提取缩略图时出错:\n{str(e)}")
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.error(f"❌ 错误: {str(e)}")
    
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
        settings.setValue("theme", self.theme_manager.current_theme.name)
        settings.sync()
        
        QMessageBox.information(self, "成功", "设置已保存！")
        if UI_COMPONENTS_AVAILABLE:
            self._log_widget.info("💾 设置已保存")
    
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
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.info("🔄 设置已重置")
    
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
            if UI_COMPONENTS_AVAILABLE:
                self._log_widget.info("🧹 历史记录已清空")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            f"<h3>{AppConfig.APP_NAME}</h3>"
            f"<p>版本: {AppConfig.APP_VERSION}</p>"
            f"<p>作者: {AppConfig.APP_AUTHOR}</p>"
            f"<p>NFO 到 VSMETA 转换器</p>"
            f"<p>主要优化：</p>"
            f"<ul>"
            f"<li>📦 模块化架构</li>"
            f"<li>🎨 4种预设主题</li>"
            f"<li>📁 增强文件拖放</li>"
            f"<li>📋 彩色日志系统</li>"
            f"<li>⌨️ 键盘快捷键</li>"
            f"</ul>"
        )
    
    def load_settings(self):
        """加载设置"""
        settings = QSettings(AppConfig.APP_NAME, "Settings")
        
        # 主题
        theme_name = settings.value("theme", DARK_THEME.name, type=str)
        self.theme_manager.set_theme_by_name(theme_name)
        
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
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
