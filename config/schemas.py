#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置数据模型和 Schema 定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ThemeMode(Enum):
    """主题模式"""
    DARK = "dark"
    LIGHT = "light"
    OCEAN = "ocean"
    FOREST = "forest"


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


@dataclass
class ConverterConfig:
    """转换器配置"""
    directories: List[str] = field(default_factory=lambda: ["."])
    max_workers: int = 4
    max_image_size_kb: int = 200
    image_compression_ratio: float = 0.8
    auto_backup: bool = True
    backup_path: Optional[str] = None
    skip_existing: bool = True
    overwrite_nfo: bool = False
    generate_sample: bool = False

    def validate(self):
        """验证配置"""
        if self.max_workers < 1:
            self.max_workers = 1
        elif self.max_workers > 32:
            self.max_workers = 32

        if self.image_compression_ratio < 0.1:
            self.image_compression_ratio = 0.1
        elif self.image_compression_ratio > 1.0:
            self.image_compression_ratio = 1.0

        if self.max_image_size_kb < 50:
            self.max_image_size_kb = 50
        elif self.max_image_size_kb > 10000:
            self.max_image_size_kb = 10000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "directories": self.directories,
            "max_workers": self.max_workers,
            "max_image_size_kb": self.max_image_size_kb,
            "image_compression_ratio": self.image_compression_ratio,
            "auto_backup": self.auto_backup,
            "backup_path": self.backup_path,
            "skip_existing": self.skip_existing,
            "overwrite_nfo": self.overwrite_nfo,
            "generate_sample": self.generate_sample,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConverterConfig":
        """从字典创建"""
        return cls(
            directories=data.get("directories", ["."]),
            max_workers=data.get("max_workers", 4),
            max_image_size_kb=data.get("max_image_size_kb", 200),
            image_compression_ratio=data.get("image_compression_ratio", 0.8),
            auto_backup=data.get("auto_backup", True),
            backup_path=data.get("backup_path"),
            skip_existing=data.get("skip_existing", True),
            overwrite_nfo=data.get("overwrite_nfo", False),
            generate_sample=data.get("generate_sample", False),
        )


@dataclass
class UIConfig:
    """UI 配置"""
    theme: ThemeMode = ThemeMode.DARK
    auto_scroll: bool = True
    window_width: int = 1280
    window_height: int = 800
    window_maximized: bool = False
    show_advanced: bool = False
    recent_directories: List[str] = field(default_factory=list)
    max_recent_directories: int = 10

    def validate(self):
        """验证配置"""
        if self.window_width < 800:
            self.window_width = 800
        elif self.window_width > 3840:
            self.window_width = 3840

        if self.window_height < 600:
            self.window_height = 600
        elif self.window_height > 2160:
            self.window_height = 2160

        if self.max_recent_directories < 5:
            self.max_recent_directories = 5
        elif self.max_recent_directories > 50:
            self.max_recent_directories = 50

    def add_recent_directory(self, path: str):
        """添加最近目录"""
        if path in self.recent_directories:
            self.recent_directories.remove(path)
        self.recent_directories.insert(0, path)

        if len(self.recent_directories) > self.max_recent_directories:
            self.recent_directories = self.recent_directories[:self.max_recent_directories]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "theme": self.theme.value,
            "auto_scroll": self.auto_scroll,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_maximized": self.window_maximized,
            "show_advanced": self.show_advanced,
            "recent_directories": self.recent_directories,
            "max_recent_directories": self.max_recent_directories,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UIConfig":
        """从字典创建"""
        try:
            theme = ThemeMode(data.get("theme", "dark"))
        except (ValueError, KeyError):
            theme = ThemeMode.DARK

        return cls(
            theme=theme,
            auto_scroll=data.get("auto_scroll", True),
            window_width=data.get("window_width", 1280),
            window_height=data.get("window_height", 800),
            window_maximized=data.get("window_maximized", False),
            show_advanced=data.get("show_advanced", False),
            recent_directories=data.get("recent_directories", []),
            max_recent_directories=data.get("max_recent_directories", 10),
        )


@dataclass
class PluginConfig:
    """插件配置"""
    enabled_plugins: List[str] = field(default_factory=list)
    plugin_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    plugin_order: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enabled_plugins": self.enabled_plugins,
            "plugin_settings": self.plugin_settings,
            "plugin_order": self.plugin_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginConfig":
        """从字典创建"""
        return cls(
            enabled_plugins=data.get("enabled_plugins", []),
            plugin_settings=data.get("plugin_settings", {}),
            plugin_order=data.get("plugin_order", []),
        )


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    cache_dir: Optional[str] = None
    max_cache_size_mb: int = 512
    cache_ttl_hours: int = 168  # 7天
    auto_cleanup: bool = True

    def validate(self):
        """验证配置"""
        if self.max_cache_size_mb < 64:
            self.max_cache_size_mb = 64
        elif self.max_cache_size_mb > 10240:
            self.max_cache_size_mb = 10240

        if self.cache_ttl_hours < 1:
            self.cache_ttl_hours = 1
        elif self.cache_ttl_hours > 8760:  # 1年
            self.cache_ttl_hours = 8760

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enabled": self.enabled,
            "cache_dir": self.cache_dir,
            "max_cache_size_mb": self.max_cache_size_mb,
            "cache_ttl_hours": self.cache_ttl_hours,
            "auto_cleanup": self.auto_cleanup,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheConfig":
        """从字典创建"""
        return cls(
            enabled=data.get("enabled", True),
            cache_dir=data.get("cache_dir"),
            max_cache_size_mb=data.get("max_cache_size_mb", 512),
            cache_ttl_hours=data.get("cache_ttl_hours", 168),
            auto_cleanup=data.get("auto_cleanup", True),
        )


@dataclass
class LoggingConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    log_to_file: bool = True
    log_dir: Optional[str] = None
    max_log_files: int = 10
    max_log_size_mb: int = 10
    show_timestamp: bool = True
    show_level: bool = True

    def validate(self):
        """验证配置"""
        if self.max_log_files < 1:
            self.max_log_files = 1
        elif self.max_log_files > 100:
            self.max_log_files = 100

        if self.max_log_size_mb < 1:
            self.max_log_size_mb = 1
        elif self.max_log_size_mb > 100:
            self.max_log_size_mb = 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "level": self.level.value,
            "log_to_file": self.log_to_file,
            "log_dir": self.log_dir,
            "max_log_files": self.max_log_files,
            "max_log_size_mb": self.max_log_size_mb,
            "show_timestamp": self.show_timestamp,
            "show_level": self.show_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingConfig":
        """从字典创建"""
        try:
            level = LogLevel(data.get("level", "INFO"))
        except (ValueError, KeyError):
            level = LogLevel.INFO

        return cls(
            level=level,
            log_to_file=data.get("log_to_file", True),
            log_dir=data.get("log_dir"),
            max_log_files=data.get("max_log_files", 10),
            max_log_size_mb=data.get("max_log_size_mb", 10),
            show_timestamp=data.get("show_timestamp", True),
            show_level=data.get("show_level", True),
        )


@dataclass
class ConfigSchema:
    """完整配置 Schema"""
    version: str = "1.0"
    converter: ConverterConfig = field(default_factory=ConverterConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def validate_all(self):
        """验证所有配置"""
        self.converter.validate()
        self.ui.validate()
        self.cache.validate()
        self.logging.validate()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "converter": self.converter.to_dict(),
            "ui": self.ui.to_dict(),
            "plugins": self.plugins.to_dict(),
            "cache": self.cache.to_dict(),
            "logging": self.logging.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigSchema":
        """从字典创建"""
        return cls(
            version=data.get("version", "1.0"),
            converter=ConverterConfig.from_dict(data.get("converter", {})),
            ui=UIConfig.from_dict(data.get("ui", {})),
            plugins=PluginConfig.from_dict(data.get("plugins", {})),
            cache=CacheConfig.from_dict(data.get("cache", {})),
            logging=LoggingConfig.from_dict(data.get("logging", {})),
        )
