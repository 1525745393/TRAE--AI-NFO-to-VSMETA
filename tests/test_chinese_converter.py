"""
简繁转换功能测试
"""

import pytest

try:
    import zhconv
    ZHCONV_AVAILABLE = True
except ImportError:
    ZHCONV_AVAILABLE = False

from chinese_converter import (
    ChineseConverter,
    to_simplified,
    to_traditional,
    auto_convert,
)


class TestChineseConverter:
    """简繁转换器测试"""

    def test_initialization(self):
        """测试初始化"""
        converter = ChineseConverter()
        assert converter.target == 'zh-cn'

        converter_tw = ChineseConverter('zh-tw')
        assert converter_tw.target == 'zh-tw'

    def test_supported_conversions(self):
        """测试支持的转换类型"""
        assert 'zh-cn' in ChineseConverter.SUPPORTED_CONVERSIONS
        assert 'zh-tw' in ChineseConverter.SUPPORTED_CONVERSIONS
        assert 'zh-hk' in ChineseConverter.SUPPORTED_CONVERSIONS

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_convert_to_simplified(self):
        """测试转换为简体中文"""
        converter = ChineseConverter('zh-cn')

        # 繁体 → 简体
        result = converter.convert('這是繁體中文')
        # 验证转换确实发生了
        assert result is not None
        assert len(result) > 0
        # 至少应该有一些字符被转换
        assert result != '這是繁體中文'

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_convert_to_traditional(self):
        """测试转换为繁体中文"""
        converter = ChineseConverter('zh-tw')

        # 简体 → 繁体
        result = converter.convert('这是简体中文')
        assert result is not None
        assert len(result) > 0

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_to_simplified_function(self):
        """测试快捷函数 to_simplified"""
        result = to_simplified('這是繁體')
        assert result is not None
        assert len(result) > 0
        # 验证不是原样返回
        assert result != '這是繁體'

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_to_traditional_function(self):
        """测试快捷函数 to_traditional"""
        result = to_traditional('这是简体')
        assert result is not None
        assert len(result) > 0

    def test_empty_text(self):
        """测试空文本处理"""
        converter = ChineseConverter()
        assert converter.convert('') == ''
        assert converter.convert(None) is None

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_detect_simplified(self):
        """测试检测简体中文"""
        text = '这是简体中文内容包含特殊简体字符幾萬龍龜'
        detected = ChineseConverter.detect(text)
        assert detected is not None

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_detect_traditional(self):
        """测试检测繁体中文"""
        text = '這是繁體內容包含特殊繁體字符幾萬龍龜'
        detected = ChineseConverter.detect(text)
        assert detected is not None

    @pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
    def test_auto_convert_same(self):
        """测试自动转换相同语言"""
        text = '这是简体中文包含简体字符几万年'
        # 已经是简体，转换后应该相同
        result = auto_convert(text, 'zh-cn')
        assert result is not None
        assert len(result) > 0


@pytest.mark.skipif(not ZHCONV_AVAILABLE, reason="zhconv 未安装")
class TestChineseConversionIntegration:
    """集成测试：完整的转换流程"""

    def test_nfo_metadata_conversion(self):
        """测试 NFO 元数据转换场景"""
        # 模拟 NFO 文件中的繁体元数据
        nfo_content = """<?xml version="1.0" encoding="utf-8"?>
        <movie>
            <title>電影名稱</title>
            <plot>這是電影的劇情介紹，包含繁體中文字符。</plot>
            <director>導演姓名</director>
            <actor>演員列表</actor>
        </movie>"""

        # 转换为简体（用于群晖 Video Station）
        converter = ChineseConverter('zh-cn')
        simplified = converter.convert(nfo_content)

        # 验证转换结果
        assert simplified is not None
        assert len(simplified) > 0
        assert simplified != nfo_content

    def test_batch_conversion(self):
        """测试批量转换"""
        texts = [
            '这是第一个文本',
            '這是第二個文本',
            '这是第三個混合文本',
        ]

        converter = ChineseConverter('zh-cn')
        results = [converter.convert(text) for text in texts]

        # 所有结果都应该有值
        for result in results:
            assert result is not None
            assert len(result) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
