#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例插件：文件大小过滤器
================================

功能：根据文件大小过滤视频文件，跳过过小或过大的文件。

使用方法：
1. 将此文件放入 plugins/ 目录
2. 启动转换器时使用 --load-plugins 参数自动加载
3. 或在菜单中选择"插件管理"手动加载

插件类型：FileFilterPlugin（文件过滤）
"""

import logging
import os
from abc import ABC


class FileSizeFilterPlugin(ABC):
    """
    文件大小过滤器插件

    可配置最小和最大文件大小，不符合要求的文件将被跳过。
    阈值可通过 Config 的 plugin_settings 字段配置。

    配置示例（在 config.json 中）：
    {
        "plugin_settings": {
            "file_size_filter": {
                "min_size_mb": 100,
                "max_size_mb": 10000
            }
        }
    }
    """

    # 默认阈值
    DEFAULT_MIN_SIZE_MB = 100  # 100MB
    DEFAULT_MAX_SIZE_MB = 10000  # 10GB

    @property
    def name(self) -> str:
        return "file_size_filter"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "按文件大小过滤视频文件"

    def on_register(self, config=None):
        """注册时读取配置"""
        self._logger = logging.getLogger(f"plugin.{self.name}")
        self._min_size = self.DEFAULT_MIN_SIZE_MB
        self._max_size = self.DEFAULT_MAX_SIZE_MB

        # 从配置中读取自定义阈值
        if config and hasattr(config, "plugin_settings"):
            settings = config.plugin_settings.get(self.name, {})
            self._min_size = settings.get("min_size_mb", self._min_size)
            self._max_size = settings.get("max_size_mb", self._max_size)

        self._min_bytes = self._min_size * 1024 * 1024
        self._max_bytes = self._max_size * 1024 * 1024

        self._logger.info(
            f"插件 [{self.name}] v{self.version} 已注册 "
            f"(最小: {self._min_size}MB, 最大: {self._max_size}MB)"
        )

    def on_unregister(self):
        """注销"""
        self._logger.info(f"插件 [{self.name}] 已注销")

    def should_process(self, filepath: str, filename: str) -> bool:
        """
        判断文件是否应该被处理

        Args:
            filepath: 文件完整路径
            filename: 文件名

        Returns:
            True 表示应该处理，False 表示跳过
        """
        try:
            size = os.path.getsize(filepath)
            size_mb = size / (1024 * 1024)

            if size < self._min_bytes:
                self._logger.debug(
                    f"跳过（过小）: {filename} ({size_mb:.1f}MB < {self._min_size}MB)"
                )
                return False

            if self._max_bytes > 0 and size > self._max_bytes:
                self._logger.debug(
                    f"跳过（过大）: {filename} ({size_mb:.1f}MB > {self._max_size}MB)"
                )
                return False

            return True

        except OSError as e:
            self._logger.warning(f"无法获取文件大小: {filename}: {e}")
            return True  # 获取失败时默认处理


# 导出插件实例
plugin_instance = FileSizeFilterPlugin()
