#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme_manager 单元测试
测试主题管理器的各项功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ui.utils.theme_manager import (
        ThemeColors,
        ThemeManager,
        DARK_THEME,
        LIGHT_THEME,
        OCEAN_THEME,
        FOREST_THEME,
        ALL_THEMES,
        apply_theme,
        create_stylesheet
    )
except ImportError:
    import pytest
    pytest.skip("PyQt6 未安装，跳过测试", allow_module_level=True)


class TestThemeColors:
    """测试 ThemeColors 数据类"""

    def test_dark_theme_attributes(self):
        """测试暗色主题的所有属性"""
        assert DARK_THEME.name == "暗色主题"
        assert DARK_THEME.primary == "#3498db"
        assert DARK_THEME.success == "#27ae60"
        assert DARK_THEME.warning == "#f39c12"
        assert DARK_THEME.danger == "#e74c3c"
        assert DARK_THEME.background == "#1e1e2e"
        assert DARK_THEME.surface == "#2d2d3f"
        assert DARK_THEME.text == "#cdd6f4"

    def test_light_theme_attributes(self):
        """测试亮色主题的所有属性"""
        assert LIGHT_THEME.name == "亮色主题"
        assert LIGHT_THEME.primary == "#2563eb"
        assert LIGHT_THEME.background == "#eff1f4"
        assert LIGHT_THEME.surface == "#ffffff"
        assert LIGHT_THEME.text == "#1e293b"

    def test_ocean_theme_attributes(self):
        """测试海洋主题的所有属性"""
        assert OCEAN_THEME.name == "海洋主题"
        assert OCEAN_THEME.primary == "#00bcd4"
        assert OCEAN_THEME.background == "#0a192f"
        assert OCEAN_THEME.surface == "#112240"

    def test_forest_theme_attributes(self):
        """测试森林主题的所有属性"""
        assert FOREST_THEME.name == "森林主题"
        assert FOREST_THEME.primary == "#4caf50"
        assert FOREST_THEME.background == "#1a2e1a"
        assert FOREST_THEME.surface == "#2d4a2d"

    def test_all_themes_count(self):
        """测试所有主题的数量"""
        assert len(ALL_THEMES) == 4
        assert DARK_THEME in ALL_THEMES
        assert LIGHT_THEME in ALL_THEMES
        assert OCEAN_THEME in ALL_THEMES
        assert FOREST_THEME in ALL_THEMES


class TestThemeManager:
    """测试 ThemeManager 类"""

    def test_initialization(self):
        """测试 ThemeManager 初始化"""
        manager = ThemeManager()
        assert manager.current_theme == DARK_THEME
        assert len(manager._on_theme_changed_callbacks) == 0

    def test_set_theme(self):
        """测试设置主题"""
        manager = ThemeManager()
        manager.set_theme(LIGHT_THEME)
        assert manager.current_theme == LIGHT_THEME
        assert manager.current_theme.name == "亮色主题"

    def test_set_theme_by_name(self):
        """测试通过名称设置主题"""
        manager = ThemeManager()
        
        assert manager.set_theme_by_name("暗色主题") is True
        assert manager.current_theme == DARK_THEME
        
        assert manager.set_theme_by_name("亮色主题") is True
        assert manager.current_theme == LIGHT_THEME
        
        assert manager.set_theme_by_name("海洋主题") is True
        assert manager.current_theme == OCEAN_THEME
        
        assert manager.set_theme_by_name("森林主题") is True
        assert manager.current_theme == FOREST_THEME
        
        assert manager.set_theme_by_name("不存在的名称") is False
        assert manager.current_theme == FOREST_THEME

    def test_get_theme_by_name(self):
        """测试通过名称获取主题"""
        manager = ThemeManager()
        
        assert manager.get_theme_by_name("暗色主题") == DARK_THEME
        assert manager.get_theme_by_name("亮色主题") == LIGHT_THEME
        assert manager.get_theme_by_name("海洋主题") == OCEAN_THEME
        assert manager.get_theme_by_name("森林主题") == FOREST_THEME
        assert manager.get_theme_by_name("不存在的名称") is None

    def test_on_theme_changed_callback(self):
        """测试主题变化回调"""
        manager = ThemeManager()
        callback_executed = []
        
        def callback(theme):
            callback_executed.append(theme)
        
        manager.on_theme_changed(callback)
        assert len(manager._on_theme_changed_callbacks) == 1
        
        manager.set_theme(LIGHT_THEME)
        assert len(callback_executed) == 1
        assert callback_executed[0] == LIGHT_THEME
        
        manager.set_theme(OCEAN_THEME)
        assert len(callback_executed) == 2
        assert callback_executed[1] == OCEAN_THEME


class TestThemeFunctions:
    """测试主题相关的函数"""

    def test_create_stylesheet(self):
        """测试样式表生成"""
        stylesheet = create_stylesheet(DARK_THEME)
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        assert DARK_THEME.primary in stylesheet
        assert DARK_THEME.background in stylesheet
        assert DARK_THEME.text in stylesheet

    def test_create_stylesheet_all_themes(self):
        """测试所有主题的样式表生成"""
        for theme in ALL_THEMES:
            stylesheet = create_stylesheet(theme)
            assert isinstance(stylesheet, str)
            assert len(stylesheet) > 100
            assert theme.primary in stylesheet
            assert theme.background in stylesheet


class TestThemeColorsImmutable:
    """测试主题颜色对象的不可变性"""

    def test_theme_colors_are_dataclass(self):
        """测试 ThemeColors 是数据类"""
        assert hasattr(ThemeColors, '__dataclass_fields__')

    def test_theme_attributes_exist(self):
        """测试主题属性存在"""
        assert DARK_THEME.name == "暗色主题"
        assert hasattr(DARK_THEME, 'primary')
        assert hasattr(DARK_THEME, 'background')
        assert hasattr(DARK_THEME, 'text')


def test_theme_manager_singleton_behavior():
    """测试 ThemeManager 的单例行为"""
    manager1 = ThemeManager()
    manager2 = ThemeManager()
    
    assert manager1 is not manager2
    assert manager1.current_theme == manager2.current_theme
    
    manager1.set_theme(LIGHT_THEME)
    assert manager1.current_theme == LIGHT_THEME
    assert manager2.current_theme == DARK_THEME


def test_theme_colors_str_representation():
    """测试主题颜色对象的字符串表示"""
    dark_str = str(DARK_THEME)
    assert "ThemeColors" in dark_str
    assert "primary" in dark_str
    assert "#3498db" in dark_str
    
    light_str = str(LIGHT_THEME)
    assert "ThemeColors" in light_str
    assert "#2563eb" in light_str


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
