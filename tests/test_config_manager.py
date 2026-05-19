#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理系统测试
"""

import pytest
import os
import tempfile
import json
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.manager import ConfigManager, get_config_manager
from config.schemas import (
    ConfigSchema,
    ConverterConfig,
    UIConfig,
    PluginConfig,
    CacheConfig,
    LoggingConfig,
    ThemeMode,
    LogLevel,
)
from config.exceptions import (
    ConfigNotFoundError,
    ConfigValidationError,
    ConfigSaveError,
    ConfigLoadError,
)


class TestConfigSchemas:
    """测试配置数据模型"""

    def test_converter_config_defaults(self):
        """测试转换器配置默认值"""
        config = ConverterConfig()
        assert config.directories == ["."]
        assert config.max_workers == 4
        assert config.max_image_size_kb == 200
        assert config.image_compression_ratio == 0.8

    def test_converter_config_validation(self):
        """测试转换器配置验证"""
        config = ConverterConfig(max_workers=0)
        config.validate()
        assert config.max_workers == 1

        config = ConverterConfig(max_workers=100)
        config.validate()
        assert config.max_workers == 32

        config = ConverterConfig(image_compression_ratio=0)
        config.validate()
        assert config.image_compression_ratio == 0.1

    def test_converter_config_dict_roundtrip(self):
        """测试转换器配置字典往返"""
        config = ConverterConfig(max_workers=8, directories=["/test/path"])
        data = config.to_dict()
        restored = ConverterConfig.from_dict(data)

        assert restored.max_workers == 8
        assert restored.directories == ["/test/path"]

    def test_ui_config_theme_enum(self):
        """测试 UI 配置主题枚举"""
        config = UIConfig(theme=ThemeMode.OCEAN)
        assert config.theme == ThemeMode.OCEAN
        assert config.to_dict()["theme"] == "ocean"

    def test_ui_config_recent_directories(self):
        """测试 UI 最近目录"""
        config = UIConfig()
        config.add_recent_directory("/path/1")
        config.add_recent_directory("/path/2")
        config.add_recent_directory("/path/1")

        assert config.recent_directories[0] == "/path/1"
        assert len(config.recent_directories) == 2

    def test_full_config_schema(self):
        """测试完整配置 schema"""
        schema = ConfigSchema()
        assert schema.version == "1.0"
        assert isinstance(schema.converter, ConverterConfig)
        assert isinstance(schema.ui, UIConfig)
        assert isinstance(schema.plugins, PluginConfig)
        assert isinstance(schema.cache, CacheConfig)
        assert isinstance(schema.logging, LoggingConfig)


class TestConfigManager:
    """测试配置管理器"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        mgr1 = ConfigManager()
        mgr2 = ConfigManager()
        assert mgr1 is mgr2

    def test_config_manager_init(self, tmp_path):
        """测试配置管理器初始化"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        assert mgr.config_dir.exists()
        assert mgr.config_file.parent == config_dir

    def test_default_config_creation(self, tmp_path):
        """测试默认配置创建"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir))

        assert mgr.config_file.exists()
        assert isinstance(mgr.config, ConfigSchema)

    def test_config_save_and_load(self, tmp_path):
        """测试配置保存和加载"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        mgr.config.converter.max_workers = 8
        mgr.config.ui.theme = ThemeMode.LIGHT
        mgr.save()

        mgr2 = ConfigManager(config_dir=str(config_dir))
        assert mgr2.config.converter.max_workers == 8
        assert mgr2.config.ui.theme == ThemeMode.LIGHT

    def test_config_validation_on_save(self, tmp_path):
        """测试配置保存时验证"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        mgr.config.converter.max_workers = 0
        mgr.save()

        assert mgr.config.converter.max_workers == 1

    def test_get_set_value(self, tmp_path):
        """测试获取和设置配置值"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        mgr.set_value("converter.max_workers", 12, auto_save=False)
        assert mgr.get_value("converter.max_workers") == 12

        mgr.set_value("ui.theme", ThemeMode.OCEAN, auto_save=False)
        assert mgr.get_value("ui.theme") == ThemeMode.OCEAN

    def test_get_value_default(self, tmp_path):
        """测试获取配置值默认值"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        assert mgr.get_value("nonexistent.key", "default") == "default"

    def test_change_listener(self, tmp_path):
        """测试配置变更监听器"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        callback_called = False
        callback_config = None

        def on_change(config):
            nonlocal callback_called, callback_config
            callback_called = True
            callback_config = config

        mgr.on_change("test_listener", on_change)
        mgr.config.converter.max_workers = 10
        mgr.save()

        assert callback_called
        assert callback_config is not None

        mgr.remove_on_change("test_listener")

    def test_reset_to_default(self, tmp_path):
        """测试重置为默认配置"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        mgr.config.converter.max_workers = 15
        mgr.reset_to_default()

        assert mgr.config.converter.max_workers == 4

    def test_export_schema(self, tmp_path):
        """测试导出配置 schema"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        schema = mgr.export_schema()
        assert "version" in schema
        assert "converter" in schema
        assert "ui" in schema


class TestConfigExceptions:
    """测试配置异常"""

    def test_load_nonexistent_file(self, tmp_path):
        """测试加载不存在的文件"""
        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        with pytest.raises(ConfigNotFoundError):
            mgr.load(str(tmp_path / "nonexistent.json"))

    def test_load_corrupted_file(self, tmp_path):
        """测试加载损坏的文件"""
        bad_file = tmp_path / "bad.json"
        with open(bad_file, "w") as f:
            f.write("{invalid json}")

        config_dir = tmp_path / "test_config"
        mgr = ConfigManager(config_dir=str(config_dir), auto_load=False)

        with pytest.raises(ConfigLoadError):
            mgr.load(str(bad_file))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
