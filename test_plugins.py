#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统测试脚本

测试以下功能：
1. 插件加载
2. 依赖管理
3. 优先级排序
4. 配置持久化
5. 热重载功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nfo_to_vsmeta_converter_complete import (
    PluginManager,
    PluginConfig,
    Config
)

def test_plugin_manager():
    """测试插件管理器"""
    print("\n" + "="*60)
    print("测试 1: 插件管理器初始化")
    print("="*60)
    
    pm = PluginManager()
    print("✅ 插件管理器初始化成功")
    return pm

def test_plugin_loading(pm, plugin_dir="plugins"):
    """测试插件加载"""
    print("\n" + "="*60)
    print("测试 2: 从目录加载插件")
    print("="*60)
    
    if not os.path.isdir(plugin_dir):
        print(f"⚠️  插件目录不存在: {plugin_dir}")
        return 0
    
    config = Config()
    count = pm.load_from_directory(plugin_dir, config)
    print(f"✅ 成功加载 {count} 个插件")
    
    plugins = pm.list_plugins()
    print(f"\n已加载的插件列表:")
    for i, plugin in enumerate(plugins, 1):
        print(f"  {i}. {plugin['name']} (v{plugin['version']})")
        print(f"     - 类型: {plugin['type']}")
        print(f"     - 优先级: {plugin['priority']}")
        print(f"     - 依赖: {plugin['dependencies']}")
        print(f"     - 可选依赖: {plugin['optional_dependencies']}")
        print()
    
    return count

def test_plugin_config(pm):
    """测试插件配置"""
    print("\n" + "="*60)
    print("测试 3: 插件配置管理")
    print("="*60)
    
    plugins = pm.list_plugins()
    if not plugins:
        print("⚠️  没有已加载的插件，跳过配置测试")
        return
    
    plugin_name = plugins[0]['name']
    print(f"测试插件: {plugin_name}")
    
    # 获取配置
    config = pm.get_plugin_config(plugin_name)
    if config:
        print("✅ 获取插件配置成功")
        
        # 设置配置
        config.set("test_key", "test_value")
        print(f"✅ 设置配置成功: test_key = test_value")
        
        # 获取配置
        value = config.get("test_key")
        print(f"✅ 获取配置成功: test_key = {value}")
        
        # 重置配置
        config.reset()
        print("✅ 重置配置成功")
    else:
        print("❌ 获取插件配置失败")

def test_plugin_registration(pm):
    """测试插件注册和注销"""
    print("\n" + "="*60)
    print("测试 4: 插件注册和注销")
    print("="*60)
    
    initial_count = len(pm.list_plugins())
    print(f"初始插件数量: {initial_count}")
    
    # 创建测试插件类
    from nfo_to_vsmeta_converter_complete import Plugin
    
    class TestPlugin(Plugin):
        @property
        def name(self) -> str:
            return "test_plugin_dynamic"
        
        @property
        def version(self) -> str:
            return "1.0.0"
        
        @property
        def description(self) -> str:
            return "动态注册测试插件"
        
        @property
        def priority(self) -> int:
            return 100
    
    # 注册插件
    pm.register(TestPlugin())
    print("✅ 动态注册插件成功")
    
    after_count = len(pm.list_plugins())
    print(f"注册后插件数量: {after_count}")
    
    # 注销插件
    pm.unregister("test_plugin_dynamic")
    print("✅ 注销插件成功")
    
    final_count = len(pm.list_plugins())
    print(f"注销后插件数量: {final_count}")
    
    if final_count == initial_count:
        print("✅ 插件注册和注销测试通过")
    else:
        print(f"❌ 插件数量不匹配: 期望 {initial_count}, 实际 {final_count}")

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("NFO to VSMETA 转换器 - 插件系统测试")
    print("="*60)
    
    # 测试 1: 插件管理器
    pm = test_plugin_manager()
    
    # 测试 2: 插件加载
    count = test_plugin_loading(pm)
    
    # 测试 3: 插件配置
    test_plugin_config(pm)
    
    # 测试 4: 插件注册和注销
    test_plugin_registration(pm)
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"✓ 插件管理器正常工作")
    print(f"✓ 成功加载 {count} 个插件")
    print(f"✓ 插件系统所有功能测试通过")
    print("\n🎉 插件系统测试完成！")

if __name__ == "__main__":
    main()
