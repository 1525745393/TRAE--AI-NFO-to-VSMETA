#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主题管理工具
提供主题颜色配置和样式表生成
"""

from dataclasses import dataclass
from typing import Optional

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QSize
    from PyQt6.QtGui import QColor, QPalette
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


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


# 预设主题
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

OCEAN_THEME = ThemeColors(
    name="海洋主题",
    primary="#00bcd4",
    secondary="#009688",
    success="#4caf50",
    warning="#ff9800",
    danger="#f44336",
    info="#9c27b0",
    background="#0a192f",
    surface="#112240",
    text="#ccd6f6",
    text_secondary="#8892b0",
    border="#233554"
)

FOREST_THEME = ThemeColors(
    name="森林主题",
    primary="#4caf50",
    secondary="#8bc34a",
    success="#cddc39",
    warning="#ffeb3b",
    danger="#f44336",
    info="#9c27b0",
    background="#1a2e1a",
    surface="#2d4a2d",
    text="#c8e6c9",
    text_secondary="#a5d6a7",
    border="#4a7c4a"
)

# 所有主题列表
ALL_THEMES = [DARK_THEME, LIGHT_THEME, OCEAN_THEME, FOREST_THEME]


class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        self._current_theme: ThemeColors = DARK_THEME
        self._on_theme_changed_callbacks = []
    
    @property
    def current_theme(self) -> ThemeColors:
        return self._current_theme
    
    def set_theme(self, theme: ThemeColors):
        """设置主题"""
        self._current_theme = theme
        for callback in self._on_theme_changed_callbacks:
            callback(theme)
    
    def set_theme_by_name(self, name: str) -> bool:
        """通过名称设置主题"""
        for theme in ALL_THEMES:
            if theme.name == name:
                self.set_theme(theme)
                return True
        return False
    
    def get_theme_by_name(self, name: str) -> Optional[ThemeColors]:
        """通过名称获取主题"""
        for theme in ALL_THEMES:
            if theme.name == name:
                return theme
        return None
    
    def apply_to_app(self, app: QApplication):
        """将主题应用到应用程序"""
        apply_theme(app, self._current_theme)
    
    def create_stylesheet(self) -> str:
        """创建样式表"""
        return create_stylesheet(self._current_theme)
    
    def on_theme_changed(self, callback):
        """注册主题变化回调"""
        self._on_theme_changed_callbacks.append(callback)


def apply_theme(app: QApplication, theme: ThemeColors):
    """将主题应用到QApplication"""
    palette = QPalette()
    
    bg_color = QColor(theme.background)
    surface_color = QColor(theme.surface)
    text_color = QColor(theme.text)
    text_sec_color = QColor(theme.text_secondary)
    border_color = QColor(theme.border)
    primary_color = QColor(theme.primary)
    
    palette.setColor(QPalette.ColorRole.Window, bg_color)
    palette.setColor(QPalette.ColorRole.WindowText, text_color)
    palette.setColor(QPalette.ColorRole.Base, surface_color)
    palette.setColor(QPalette.ColorRole.AlternateBase, bg_color.lighter(110))
    palette.setColor(QPalette.ColorRole.ToolTipBase, surface_color)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_color)
    palette.setColor(QPalette.ColorRole.Text, text_color)
    palette.setColor(QPalette.ColorRole.Button, surface_color)
    palette.setColor(QPalette.ColorRole.ButtonText, text_color)
    palette.setColor(QPalette.ColorRole.BrightText, QColor("white"))
    palette.setColor(QPalette.ColorRole.Highlight, primary_color)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    
    app.setPalette(palette)


def create_stylesheet(theme: ThemeColors) -> str:
    """创建QSS样式表"""
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
    
    QPushButton#success:hover {{
        background-color: {QColor(theme.success).lighter(115).name()};
    }}
    
    QPushButton#danger {{
        background-color: {theme.danger};
    }}
    
    QPushButton#danger:hover {{
        background-color: {QColor(theme.danger).lighter(115).name()};
    }}
    
    QPushButton#secondary {{
        background-color: {theme.secondary};
    }}
    
    QPushButton#secondary:hover {{
        background-color: {QColor(theme.secondary).lighter(115).name()};
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
    
    QMenu {{
        background-color: {theme.surface};
        border: 1px solid {theme.border};
        border-radius: 6px;
        padding: 4px;
    }}
    
    QMenu::item {{
        padding: 6px 24px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {theme.primary};
        color: white;
    }}
    """
