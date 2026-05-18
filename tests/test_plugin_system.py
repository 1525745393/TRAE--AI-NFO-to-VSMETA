#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统单元测试
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nfo_to_vsmeta_converter_complete import (
    PluginManager,
    Plugin,
    MetadataEnhancerPlugin,
    FileFilterPlugin,
    LifecyclePlugin
)


class TestPluginBase:
    """测试 Plugin 基类"""

    def test_plugin_abstract_methods(self):
        """测试插件抽象方法"""
        with pytest.raises(TypeError):
            Plugin()

    def test_plugin_properties(self):
        """测试插件基本属性"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试插件"

        plugin = TestPlugin()
        assert plugin.name == "test"
        assert plugin.version == "1.0.0"
        assert plugin.description == "测试插件"

    def test_default_dependencies(self):
        """测试默认依赖为空"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试插件"

        plugin = TestPlugin()
        assert plugin.dependencies == []
        assert plugin.optional_dependencies == []

    def test_default_priority(self):
        """测试默认优先级"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试插件"

        plugin = TestPlugin()
        assert plugin.priority == 50

    def test_config_schema_default(self):
        """测试默认配置 schema 为空"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试插件"

        plugin = TestPlugin()
        assert plugin.config_schema == {}


class TestPluginManager:
    """测试插件管理器"""

    def test_initialization(self):
        """测试插件管理器初始化"""
        pm = PluginManager()
        assert pm is not None
        assert len(pm.list_plugins()) == 0

    def test_register_plugin(self):
        """测试插件注册"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test_register"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试注册"

        pm = PluginManager()
        plugin = TestPlugin()
        pm.register(plugin)

        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]['name'] == "test_register"

    def test_unregister_plugin(self):
        """测试插件注销"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test_unregister"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试注销"

        pm = PluginManager()
        plugin = TestPlugin()
        pm.register(plugin)
        assert len(pm.list_plugins()) == 1

        pm.unregister("test_unregister")
        assert len(pm.list_plugins()) == 0

    def test_get_plugin(self):
        """测试获取插件"""
        class TestPlugin(Plugin):
            @property
            def name(self):
                return "test_get"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试获取"

        pm = PluginManager()
        plugin = TestPlugin()
        pm.register(plugin)

        retrieved = pm.get_plugin("test_get")
        assert retrieved is not None
        assert retrieved.name == "test_get"

    def test_priority_sorting(self):
        """测试优先级排序"""
        class LowPriorityPlugin(Plugin):
            @property
            def name(self):
                return "low_priority"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "低优先级"

            @property
            def priority(self):
                return 10

        class HighPriorityPlugin(Plugin):
            @property
            def name(self):
                return "high_priority"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "高优先级"

            @property
            def priority(self):
                return 100

        pm = PluginManager()
        pm.register(LowPriorityPlugin())
        pm.register(HighPriorityPlugin())

        plugins = pm.list_plugins()
        assert plugins[0]['name'] == "high_priority"
        assert plugins[1]['name'] == "low_priority"


class TestMetadataEnhancerPlugin:
    """测试元数据增强插件基类"""

    def test_enhance_method_required(self):
        """测试 enhance 方法是抽象的"""
        with pytest.raises(TypeError):
            MetadataEnhancerPlugin()


class TestFileFilterPlugin:
    """测试文件过滤插件基类"""

    def test_should_process_method_required(self):
        """测试 should_process 方法是抽象的"""
        with pytest.raises(TypeError):
            FileFilterPlugin()


class TestLifecyclePlugin:
    """测试生命周期插件基类"""

    def test_lifecycle_methods_exist(self):
        """测试生命周期方法存在"""

        class TestLifecyclePlugin(LifecyclePlugin):
            @property
            def name(self):
                return "test_lifecycle"

            @property
            def version(self):
                return "1.0.0"

            @property
            def description(self):
                return "测试生命周期"

        plugin = TestLifecyclePlugin()
        assert hasattr(plugin, 'on_start')
        assert hasattr(plugin, 'on_file_start')
        assert hasattr(plugin, 'on_file_end')
        assert hasattr(plugin, 'on_finish')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
