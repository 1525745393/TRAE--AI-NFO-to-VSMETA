#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理单元测试
"""

import sys
import os
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nfo_to_vsmeta_converter_complete import Config


class TestConfig:
    """测试配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert config.directory == ["."]
        assert config.max_workers == 4
        assert config.max_image_size_kb == 200
        assert config.image_compression_ratio == 0.8

    def test_custom_config(self):
        """测试自定义配置"""
        config = Config(
            directory="/path/to/movies",
            max_workers=8,
            max_image_size_kb=500,
            image_compression_ratio=0.9
        )
        assert config.directory == ["/path/to/movies"]
        assert config.max_workers == 8
        assert config.max_image_size_kb == 500
        assert config.image_compression_ratio == 0.9

    def test_directory_as_string(self):
        """测试目录作为字符串"""
        config = Config(directory="/path/to/movies")
        assert isinstance(config.directory, list)
        assert "/path/to/movies" in config.directory

    def test_directory_as_list(self):
        """测试目录作为列表"""
        config = Config(directory=["/path/movies", "/path/series"])
        assert isinstance(config.directory, list)
        assert len(config.directory) == 2

    def test_value_validation_workers(self):
        """测试工作线程数验证"""
        config = Config(max_workers=0)
        assert config.max_workers == 1  # 最小值

        config = Config(max_workers=100)
        assert config.max_workers == 32  # 最大值

    def test_value_validation_compression(self):
        """测试压缩比例验证"""
        config = Config(image_compression_ratio=0)
        assert config.image_compression_ratio == 0.1  # 最小值

        config = Config(image_compression_ratio=2.0)
        assert config.image_compression_ratio == 1.0  # 最大值

    def test_save_and_load(self, temp_dir):
        """测试配置保存和加载"""
        config = Config(
            directory="/test/path",
            max_workers=8,
            max_image_size_kb=300
        )

        config_path = os.path.join(temp_dir, "test_config.json")
        config.save_to_file(config_path)

        loaded_config = Config.from_file(config_path)
        assert loaded_config.directory == ["/test/path"]
        assert loaded_config.max_workers == 8
        assert loaded_config.max_image_size_kb == 300

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        config = Config.from_file("/nonexistent/path/config.json")
        assert config is not None
        assert config.directory == ["."]

    def test_save_to_file(self, temp_dir):
        """测试保存配置到文件"""
        config = Config(max_workers=6)
        config_path = os.path.join(temp_dir, "test.json")
        config.save_to_file(config_path)

        assert os.path.exists(config_path)

        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data['max_workers'] == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
