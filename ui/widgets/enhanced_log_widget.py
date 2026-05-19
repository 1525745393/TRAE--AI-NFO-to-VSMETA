#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的彩色日志组件
支持过滤、搜索、导出和更多功能
"""

from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QTextEdit, QLineEdit, QComboBox, QCheckBox, QFileDialog
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


class LogLevel:
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class EnhancedLogWidget(QWidget):
    """增强的日志组件"""
    
    # 自定义信号
    log_cleared = pyqtSignal()
    log_exported = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logs = []
        self._auto_scroll = True
        self._current_filter = "ALL"
        self._search_text = ""
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 过滤器
        filter_label = QLabel("过滤:")
        toolbar_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        toolbar_layout.addWidget(self.filter_combo)
        
        toolbar_layout.addSpacing(16)
        
        # 搜索框
        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日志内容...")
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar_layout.addWidget(self.search_input)
        
        toolbar_layout.addStretch()
        
        # 按钮
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.clicked.connect(self._on_clear)
        toolbar_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("📤 导出")
        self.export_btn.clicked.connect(self._on_export)
        toolbar_layout.addWidget(self.export_btn)
        
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self._on_auto_scroll_changed)
        toolbar_layout.addWidget(self.auto_scroll_check)
        
        layout.addLayout(toolbar_layout)
        
        # 统计信息栏
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel("日志: 0 | DEBUG: 0 | INFO: 0 | WARNING: 0 | ERROR: 0 | SUCCESS: 0")
        stats_layout.addWidget(self.stats_label)
        
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)
        
    def log(self, message: str, level: str = LogLevel.INFO):
        """添加日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            'timestamp': timestamp,
            'message': message,
            'level': level
        }
        self._logs.append(log_entry)
        self._append_log_entry(log_entry)
        self._update_stats()
        
    def debug(self, message: str):
        """DEBUG级别日志"""
        self.log(f"🔍 {message}", LogLevel.DEBUG)
    
    def info(self, message: str):
        """INFO级别日志"""
        self.log(f"ℹ️ {message}", LogLevel.INFO)
    
    def warning(self, message: str):
        """WARNING级别日志"""
        self.log(f"⚠️ {message}", LogLevel.WARNING)
    
    def error(self, message: str):
        """ERROR级别日志"""
        self.log(f"❌ {message}", LogLevel.ERROR)
    
    def success(self, message: str):
        """SUCCESS级别日志"""
        self.log(f"✅ {message}", LogLevel.SUCCESS)
    
    def _get_level_color(self, level: str) -> QColor:
        """获取日志级别颜色"""
        color_map = {
            LogLevel.DEBUG: QColor("#9b59b6"),
            LogLevel.INFO: QColor("#3498db"),
            LogLevel.WARNING: QColor("#f39c12"),
            LogLevel.ERROR: QColor("#e74c3c"),
            LogLevel.SUCCESS: QColor("#2ecc71")
        }
        return color_map.get(level, QColor("#333333"))
    
    def _append_log_entry(self, log_entry: dict):
        """添加单个日志条目"""
        # 检查过滤
        if self._current_filter != "ALL" and self._current_filter != "全部":
            if log_entry['level'] != self._current_filter:
                return
        
        # 检查搜索
        if self._search_text:
            if self._search_text.lower() not in log_entry['message'].lower():
                return
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 时间戳格式
        timestamp_format = QTextCharFormat()
        timestamp_format.setForeground(QColor("#888888"))
        
        # 消息格式
        message_format = QTextCharFormat()
        message_format.setForeground(self._get_level_color(log_entry['level']))
        
        cursor.setCharFormat(timestamp_format)
        cursor.insertText(f"[{log_entry['timestamp']}] ")
        
        cursor.setCharFormat(message_format)
        cursor.insertText(f"{log_entry['message']}\n")
        
        if self._auto_scroll:
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
    
    def _refresh_display(self):
        """刷新显示"""
        self.log_text.clear()
        for log_entry in self._logs:
            self._append_log_entry(log_entry)
    
    def _update_stats(self):
        """更新统计信息"""
        stats = {
            'total': len(self._logs),
            'DEBUG': 0,
            'INFO': 0,
            'WARNING': 0,
            'ERROR': 0,
            'SUCCESS': 0
        }
        
        for log_entry in self._logs:
            stats[log_entry['level']] = stats.get(log_entry['level'], 0) + 1
        
        self.stats_label.setText(
            f"日志: {stats['total']} | "
            f"DEBUG: {stats['DEBUG']} | "
            f"INFO: {stats['INFO']} | "
            f"WARNING: {stats['WARNING']} | "
            f"ERROR: {stats['ERROR']} | "
            f"SUCCESS: {stats['SUCCESS']}"
        )
    
    def _on_filter_changed(self, text: str):
        """过滤器变化"""
        filter_map = {
            "全部": "ALL",
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "SUCCESS": "SUCCESS"
        }
        self._current_filter = filter_map.get(text, "ALL")
        self._refresh_display()
    
    def _on_search_changed(self, text: str):
        """搜索文本变化"""
        self._search_text = text
        self._refresh_display()
    
    def _on_auto_scroll_changed(self, state: int):
        """自动滚动变化"""
        self._auto_scroll = (state == Qt.CheckState.Checked.value)
    
    def _on_clear(self):
        """清空日志"""
        self._logs = []
        self.log_text.clear()
        self._update_stats()
        self.log_cleared.emit()
    
    def _on_export(self):
        """导出日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"nfo_converter_log_{timestamp}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出日志",
            default_name,
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for log_entry in self._logs:
                        f.write(f"[{log_entry['timestamp']}] [{log_entry['level']}] {log_entry['message']}\n")
                
                self.success(f"日志已导出到: {file_path}")
                self.log_exported.emit(file_path)
            except Exception as e:
                self.error(f"导出失败: {str(e)}")
    
    def get_all_logs(self) -> list:
        """获取所有日志"""
        return self._logs.copy()
