#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例插件：元数据增强器（评分修正）
================================

功能：自动修正和增强影片元数据，包括：
- 评分范围修正（限制在 0-10）
- 年份合理性检查
- 自动填充缺失字段

使用方法：
1. 将此文件放入 plugins/ 目录
2. 启动转换器时使用 --load-plugins 参数自动加载
3. 或在菜单中选择"插件管理"手动加载

插件类型：MetadataEnhancerPlugin（元数据增强）
"""

import logging
import os
import re
from abc import ABC


class MetadataEnhancerDemoPlugin(ABC):
    """
    元数据增强器示例插件

    演示如何通过插件修改和增强元数据。
    """

    @property
    def name(self) -> str:
        return "metadata_enhancer_demo"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "自动修正和增强影片元数据（评分、年份等）"

    def on_register(self, config=None):
        """注册时初始化"""
        self._logger = logging.getLogger(f"plugin.{self.name}")
        self._enhanced_count = 0
        self._logger.info(f"插件 [{self.name}] v{self.version} 已注册")

    def on_unregister(self):
        """注销时输出统计"""
        self._logger.info(
            f"插件 [{self.name}] 已注销，共增强 {self._enhanced_count} 个文件的元数据"
        )

    def enhance(self, metadata, filepath: str):
        """
        增强元数据

        Args:
            metadata: VideoMetadata 对象
            filepath: 视频文件路径

        Returns:
            增强后的 VideoMetadata 对象
        """
        filename = os.path.basename(filepath)
        modified = False

        # === 1. 评分范围修正 ===
        if metadata.rating < 0:
            self._logger.debug(f"[{filename}] 评分修正: {metadata.rating} -> 0")
            metadata.rating = 0
            modified = True
        elif metadata.rating > 10:
            self._logger.debug(f"[{filename}] 评分修正: {metadata.rating} -> 10")
            metadata.rating = 10
            modified = True

        # === 2. 年份合理性检查 ===
        current_year = 2026
        if metadata.year < 1888:
            self._logger.debug(f"[{filename}] 年份修正: {metadata.year} -> 0（无效年份）")
            metadata.year = 0
            modified = True
        elif metadata.year > current_year + 1:
            self._logger.debug(
                f"[{filename}] 年份修正: {metadata.year} -> {current_year}（未来年份）"
            )
            metadata.year = current_year
            modified = True

        # === 3. 从文件名提取年份（如果 NFO 中缺失） ===
        if metadata.year == 0:
            year_match = re.search(r"\((\d{4})\)", filename)
            if year_match:
                year = int(year_match.group(1))
                if 1888 <= year <= current_year:
                    self._logger.info(f"[{filename}] 从文件名提取年份: {year}")
                    metadata.year = year
                    modified = True

        # === 4. 时长合理性检查 ===
        if metadata.runtime < 0:
            metadata.runtime = 0
            modified = True
        elif metadata.runtime > 600:  # 超过 10 小时
            self._logger.debug(f"[{filename}] 时长异常: {metadata.runtime} 分钟")

        # === 5. 清理空白字符 ===
        for field_name in ["title", "original_title", "plot", "tagline"]:
            value = getattr(metadata, field_name, "")
            if value and value != value.strip():
                setattr(metadata, field_name, value.strip())
                modified = True

        if modified:
            self._enhanced_count += 1

        return metadata


# 导出插件实例
plugin_instance = MetadataEnhancerDemoPlugin()
