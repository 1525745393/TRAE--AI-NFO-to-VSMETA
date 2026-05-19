"""
简繁中文转换工具模块

支持：
- 简体 → 繁体
- 繁体 → 简体
- 自动检测并转换

使用 zhconv 库实现高性能转换
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import zhconv
    ZHCONV_AVAILABLE = True
except ImportError:
    ZHCONV_AVAILABLE = False
    logger.warning("zhconv 未安装，简繁转换功能不可用。请安装：pip install zhconv")


class ChineseConverter:
    """简繁中文转换器"""

    SUPPORTED_CONVERSIONS = {
        'zh-cn': '简体',
        'zh-tw': '繁体（台湾）',
        'zh-hk': '繁体（香港）',
        'zh-sg': '简体（新加坡）',
        'zh-mo': '繁体（澳门）',
    }

    def __init__(self, target: str = 'zh-cn'):
        """
        初始化转换器

        Args:
            target: 目标语言，默认为简体中文 'zh-cn'
                   可选值：'zh-cn', 'zh-tw', 'zh-hk', 'zh-sg', 'zh-mo'
        """
        self.target = target

    def convert(self, text: str) -> str:
        """
        转换文本为指定语言

        Args:
            text: 要转换的文本

        Returns:
            转换后的文本
        """
        if not text:
            return text

        if not ZHCONV_AVAILABLE:
            logger.warning("zhconv 未安装，无法进行简繁转换")
            return text

        try:
            return zhconv.convert(text, self.target)
        except Exception as e:
            logger.error(f"简繁转换失败: {e}")
            return text

    def to_simplified(self, text: str) -> str:
        """转换为简体中文"""
        return self.convert(text)

    def to_traditional(self, text: str, locale: str = 'zh-tw') -> str:
        """转换为繁体中文"""
        return ChineseConverter(locale).convert(text)

    @staticmethod
    def detect(text: str) -> Optional[str]:
        """
        检测文本的主要语言

        Args:
            text: 要检测的文本

        Returns:
            检测到的语言代码，如果无法确定则返回 None
        """
        if not text:
            return None

        traditional_chars = set('幾萬與憂歲龍龜')
        simplified_chars = set('几万年与忧岁龙龟')

        t_count = sum(1 for char in text if char in traditional_chars)
        s_count = sum(1 for char in text if char in simplified_chars)

        if t_count > s_count:
            return 'zh-tw'
        elif s_count > t_count:
            return 'zh-cn'

        return None

    @staticmethod
    def auto_convert(text: str, target: str = 'zh-cn') -> str:
        """
        自动检测并转换文本

        Args:
            text: 要转换的文本
            target: 目标语言

        Returns:
            转换后的文本
        """
        detected = ChineseConverter.detect(text)
        if detected == target:
            return text
        return ChineseConverter(target).convert(text)


def to_simplified(text: str) -> str:
    """快捷函数：转换为简体中文"""
    return ChineseConverter('zh-cn').convert(text)


def to_traditional(text: str, locale: str = 'zh-tw') -> str:
    """快捷函数：转换为繁体中文"""
    return ChineseConverter(locale).convert(text)


def auto_convert(text: str, target: str = 'zh-cn') -> str:
    """快捷函数：自动检测并转换"""
    return ChineseConverter.auto_convert(text, target)


if __name__ == '__main__':
    test_text = "这是一个简体中文字符串"

    print("=" * 60)
    print("简繁转换测试")
    print("=" * 60)

    if not ZHCONV_AVAILABLE:
        print("❌ zhconv 未安装")
        print("   安装命令：pip install zhconv")
    else:
        print("✓ zhconv 已安装")

        print(f"\n原文：{test_text}")
        print(f"→ 繁体：{to_traditional(test_text)}")
        print(f"→ 简体：{to_simplified(test_text)}")

        print("\n支持的转换：")
        for code, name in ChineseConverter.SUPPORTED_CONVERSIONS.items():
            converted = zhconv.convert(test_text, code)
            print(f"  {name} ({code}): {converted}")
