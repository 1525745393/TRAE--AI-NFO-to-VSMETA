#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例插件：元数据日志记录器
================================

功能：在每个文件处理前后记录日志，输出详细的元数据信息。

使用方法：
1. 将此文件放入 plugins/ 目录
2. 启动转换器时使用 --load-plugins 参数自动加载
3. 或在菜单中选择"插件管理"手动加载

插件类型：LifecyclePlugin（生命周期钩子）
"""

import logging
import os
import time
from abc import ABC
from typing import Dict

# 从主程序导入插件基类
# 注意：插件文件独立运行，需要通过 sys.path 导入主程序模块
import importlib.util

# 动态导入主程序中的插件基类
_main_path = os.path.join(os.path.dirname(__file__), "..", "nfo_to_vsmeta_converter_complete.py")
_spec = importlib.util.spec_from_file_location("converter", os.path.abspath(_main_path))
_converter = importlib.util.module_from_spec(_spec)
# 不执行模块，只获取类型（避免递归导入）
# 直接从 abc 定义基类


class MetadataLoggerPlugin(ABC):
    """
    元数据日志记录器插件

    在文件处理的各个阶段记录详细日志，便于调试和审计。
    """

    @property
    def name(self) -> str:
        return "metadata_logger"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "记录每个文件的元数据和处理状态"

    def on_register(self, config=None):
        """注册时初始化日志"""
        self._logger = logging.getLogger(f"plugin.{self.name}")
        self._file_times: Dict[str, float] = {}
        self._logger.info(f"插件 [{self.name}] v{self.version} 已注册")

    def on_unregister(self):
        """注销时清理"""
        self._logger.info(f"插件 [{self.name}] 已注销")

    def on_file_start(self, filepath: str):
        """文件处理开始时记录"""
        self._file_times[filepath] = time.time()
        filename = os.path.basename(filepath)
        self._logger.info(f"开始处理: {filename}")

    def on_file_end(self, filepath: str, result: Dict):
        """文件处理结束时记录"""
        filename = os.path.basename(filepath)
        status = result.get("result", "unknown")
        elapsed = 0

        if filepath in self._file_times:
            elapsed = time.time() - self._file_times.pop(filepath)

        if status == "success":
            self._logger.info(f"处理成功: {filename} ({elapsed:.2f}s)")
        elif status == "skipped":
            self._logger.info(f"已跳过: {filename}")
        else:
            error = result.get("error", "未知错误")
            self._logger.warning(f"处理失败: {filename} | 原因: {status} | 错误: {error}")

    def on_finish(self, stats=None):
        """全部处理完成时输出摘要"""
        if stats:
            self._logger.info(
                f"处理完成 - 总计: {stats.total_files}, "
                f"成功: {stats.success_files}, "
                f"失败: {stats.failed_files}, "
                f"耗时: {stats.duration:.1f}s"
            )


# 导出插件实例（插件管理器通过此变量发现插件）
plugin_instance = MetadataLoggerPlugin()
