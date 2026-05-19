#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的文件列表组件
支持自定义信号、拖放视觉反馈和更好的用户体验
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
        QFileDialog, QMenu
    )
    from PyQt6.QtCore import (
        Qt, pyqtSignal, QPoint
    )
    from PyQt6.QtGui import (
        QDragEnterEvent, QDropEvent, QDragLeaveEvent,
        QColor, QAction
    )
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


@dataclass
class FileItem:
    """文件项数据类"""
    path: str
    status: str = "待处理"
    progress: int = 0
    error: Optional[str] = None


class EnhancedFileListWidget(QWidget):
    """增强的文件列表组件"""
    
    # 自定义信号
    file_added = pyqtSignal(str)          # 文件添加
    file_removed = pyqtSignal(str)        # 文件移除
    files_cleared = pyqtSignal()          # 清空列表
    selection_changed = pyqtSignal(list)  # 选择变化
    files_dropped = pyqtSignal(list)      # 文件拖放
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: List[FileItem] = []
        self._is_dragging = False
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ 添加文件")
        self.add_btn.setObjectName("secondary")
        self.add_btn.clicked.connect(self._on_add_files)
        toolbar_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("🗑️ 移除选中")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.clicked.connect(self._on_remove_selected)
        self.remove_btn.setEnabled(False)
        toolbar_layout.addWidget(self.remove_btn)
        
        self.clear_btn = QPushButton("🔄 清空")
        self.clear_btn.clicked.connect(self._on_clear_files)
        toolbar_layout.addWidget(self.clear_btn)
        
        toolbar_layout.addStretch()
        
        self.file_count_label = QLabel("0 个文件")
        self.file_count_label.setStyleSheet("font-weight: bold; padding: 0 8px;")
        toolbar_layout.addWidget(self.file_count_label)
        
        layout.addLayout(toolbar_layout)
        
        # 文件表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["文件名", "路径", "状态", "进度"])
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        
        # 启用拖放
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.table.dragEnterEvent = self._drag_enter_event
        self.table.dragLeaveEvent = self._drag_leave_event
        self.table.dropEvent = self._drop_event
        
        layout.addWidget(self.table)
        
        # 拖放提示标签
        self._drop_overlay = QLabel("📥 将文件拖放到此处")
        self._drop_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_overlay.setStyleSheet("""
            QLabel {
                border: 3px dashed #4a90d9;
                border-radius: 12px;
                background-color: rgba(74, 144, 217, 0.1);
                color: #4a90d9;
                font-size: 16px;
                font-weight: bold;
                padding: 40px;
            }
        """)
        self._drop_overlay.hide()
        
        # 覆盖层布局
        overlay_layout = QVBoxLayout()
        overlay_layout.addWidget(self._drop_overlay)
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        self.table.setLayout(overlay_layout)
        
    def _drag_enter_event(self, event: QDragEnterEvent):
        """拖放进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_dragging = True
            self._drop_overlay.show()
            self.table.setStyleSheet("""
                QTableWidget {
                    border: 3px solid #4a90d9;
                    background-color: rgba(74, 144, 217, 0.05);
                }
            """)
    
    def _drag_leave_event(self, event: QDragLeaveEvent):
        """拖放离开事件"""
        self._is_dragging = False
        self._drop_overlay.hide()
        self.table.setStyleSheet("")
    
    def _drop_event(self, event: QDropEvent):
        """拖放事件"""
        self._is_dragging = False
        self._drop_overlay.hide()
        self.table.setStyleSheet("")
        
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.isfile(path):
                    files.append(path)
                elif os.path.isdir(path):
                    # 遍历目录添加文件（简单实现）
                    for ext in ['.mp4', '.avi', '.mkv', '.mov', '.nfo']:
                        files.extend([str(p) for p in Path(path).rglob(f"*{ext}")])
        
        if files:
            self.add_files(files)
            self.files_dropped.emit(files)
    
    def add_file(self, path: str):
        """添加单个文件"""
        if path not in [f.path for f in self._files]:
            file_item = FileItem(path=path)
            self._files.append(file_item)
            self._update_table()
            self.file_added.emit(path)
            self._update_count()
    
    def add_files(self, paths: List[str]):
        """批量添加文件"""
        added = []
        for path in paths:
            if path not in [f.path for f in self._files]:
                file_item = FileItem(path=path)
                self._files.append(file_item)
                added.append(path)
                self.file_added.emit(path)
        
        if added:
            self._update_table()
            self._update_count()
    
    def _update_table(self):
        """更新表格显示"""
        self.table.setRowCount(len(self._files))
        
        for row, file_item in enumerate(self._files):
            # 文件名
            name_item = QTableWidgetItem(os.path.basename(file_item.path))
            name_item.setData(Qt.ItemDataRole.UserRole, file_item.path)
            self.table.setItem(row, 0, name_item)
            
            # 路径
            path_item = QTableWidgetItem(os.path.dirname(file_item.path))
            path_item.setToolTip(file_item.path)
            self.table.setItem(row, 1, path_item)
            
            # 状态
            status_item = QTableWidgetItem(file_item.status)
            status_item.setForeground(self._get_status_color(file_item.status))
            self.table.setItem(row, 2, status_item)
            
            # 进度
            progress_item = QTableWidgetItem(f"{file_item.progress}%")
            self.table.setItem(row, 3, progress_item)
    
    def _get_status_color(self, status: str) -> QColor:
        """获取状态颜色"""
        color_map = {
            "待处理": QColor("#888888"),
            "处理中": QColor("#4a90d9"),
            "完成": QColor("#2ecc71"),
            "错误": QColor("#e74c3c"),
            "警告": QColor("#f39c12")
        }
        return color_map.get(status, QColor("#888888"))
    
    def _update_count(self):
        """更新文件计数"""
        count = len(self._files)
        self.file_count_label.setText(f"{count} 个文件")
    
    def _on_add_files(self):
        """添加文件按钮点击"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;NFO文件 (*.nfo);;所有文件 (*.*)"
        )
        if files:
            self.add_files(files)
    
    def _on_remove_selected(self):
        """移除选中文件"""
        selected_rows = sorted(
            set(index.row() for index in self.table.selectedIndexes()),
            reverse=True
        )
        
        removed_files = []
        for row in selected_rows:
            file_item = self._files.pop(row)
            removed_files.append(file_item.path)
            self.file_removed.emit(file_item.path)
        
        self._update_table()
        self._update_count()
    
    def _on_clear_files(self):
        """清空所有文件"""
        self._files = []
        self._update_table()
        self._update_count()
        self.files_cleared.emit()
    
    def _on_selection_changed(self):
        """选择变化"""
        selected = self.table.selectedItems()
        self.remove_btn.setEnabled(len(selected) > 0)
        
        selected_files = []
        for index in self.table.selectedIndexes():
            if index.column() == 0:
                path = self.table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole)
                selected_files.append(path)
        
        self.selection_changed.emit(selected_files)
    
    def _on_context_menu(self, pos: QPoint):
        """右键菜单"""
        menu = QMenu(self)
        
        add_action = QAction("➕ 添加文件", self)
        add_action.triggered.connect(self._on_add_files)
        menu.addAction(add_action)
        
        if self.table.selectedItems():
            remove_action = QAction("🗑️ 移除选中", self)
            remove_action.triggered.connect(self._on_remove_selected)
            menu.addAction(remove_action)
        
        if self._files:
            clear_action = QAction("🔄 清空列表", self)
            clear_action.triggered.connect(self._on_clear_files)
            menu.addAction(clear_action)
        
        menu.exec(self.table.mapToGlobal(pos))
    
    def get_files(self) -> List[str]:
        """获取所有文件路径"""
        return [f.path for f in self._files]
    
    def get_file_items(self) -> List[FileItem]:
        """获取所有文件项"""
        return self._files.copy()
    
    def update_file_status(self, path: str, status: str, progress: int = 0):
        """更新文件状态"""
        for file_item in self._files:
            if file_item.path == path:
                file_item.status = status
                file_item.progress = progress
                self._update_table()
                break
