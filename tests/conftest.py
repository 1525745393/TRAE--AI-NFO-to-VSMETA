#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 配置和共享 fixtures
"""

import sys
import os
import tempfile
import shutil
import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nfo_to_vsmeta_converter_complete import (
    Config,
    VideoMetadata,
    PluginManager
)


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_config():
    """创建示例配置"""
    return Config(
        directory=".",
        max_workers=2,
        max_image_size_kb=200,
        image_compression_ratio=0.8
    )


@pytest.fixture
def sample_metadata():
    """创建示例元数据"""
    return VideoMetadata(
        title="测试影片",
        original_title="Test Movie",
        year=2024,
        rating=8.5,
        plot="这是一个测试影片的剧情简介",
        runtime=120,
        genres=["动作", "科幻"],
        directors=["测试导演"],
        actors=["演员A", "演员B"],
        imdb_id="tt1234567"
    )


@pytest.fixture
def plugin_manager():
    """创建插件管理器实例"""
    return PluginManager()


@pytest.fixture
def sample_nfo_content():
    """示例 NFO 文件内容"""
    return '''<?xml version="1.0" encoding="utf-8"?>
<movie>
    <title>测试影片</title>
    <originaltitle>Test Movie</originaltitle>
    <year>2024</year>
    <rating>8.5</rating>
    <plot>这是一个测试影片的剧情简介</plot>
    <runtime>120</runtime>
    <genre>动作</genre>
    <genre>科幻</genre>
    <director>测试导演</director>
    <actor>
        <name>演员A</name>
    </actor>
    <actor>
        <name>演员B</name>
    </actor>
    <imdb>tt1234567</imdb>
</movie>
'''


@pytest.fixture
def sample_nfo_file(temp_dir, sample_nfo_content):
    """创建示例 NFO 文件"""
    nfo_path = os.path.join(temp_dir, "test.nfo")
    with open(nfo_path, "w", encoding="utf-8") as f:
        f.write(sample_nfo_content)
    return nfo_path
