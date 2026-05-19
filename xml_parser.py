"""
高性能 XML 解析器模块

支持：
- lxml：高性能解析（推荐）
- defusedxml：安全解析（默认）
- xml.etree：标准库（备用）

自动检测并选择最佳可用的解析器
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# 检查可用的 XML 解析库
LXML_AVAILABLE = False
DEFUSEDXML_AVAILABLE = False
STANDARD_XML_AVAILABLE = True  # 标准库总是可用
lxml_ET = None
defused_ET = None

try:
    import lxml.etree as lxml_ET
    LXML_AVAILABLE = True
    logger.debug("lxml 可用，使用高性能 XML 解析")
except ImportError:
    logger.debug("lxml 未安装，尝试使用 defusedxml")

try:
    from defusedxml import ElementTree as defused_ET
    DEFUSEDXML_AVAILABLE = True
    logger.debug("defusedxml 可用，使用安全 XML 解析")
except ImportError:
    logger.debug("defusedxml 未安装，使用标准库解析")

import xml.etree.ElementTree as std_ET


class XMLParser:
    """高性能 XML 解析器，支持多种后端"""

    def __init__(self, prefer_performance: bool = True):
        """
        初始化 XML 解析器

        Args:
            prefer_performance: 是否优先选择性能而非安全
                               True  = 优先 lxml (高性能)
                               False = 优先 defusedxml (安全)
        """
        self.prefer_performance = prefer_performance
        self.ET = self._select_parser()
        self._init_parser()

    def _select_parser(self):
        """选择最佳的 XML 解析器"""
        if self.prefer_performance and LXML_AVAILABLE and lxml_ET is not None:
            logger.info("使用 lxml 高性能 XML 解析器")
            return lxml_ET
        elif DEFUSEDXML_AVAILABLE and defused_ET is not None:
            logger.info("使用 defusedxml 安全 XML 解析器")
            return defused_ET
        else:
            logger.warning("使用标准库 XML 解析器（可能不安全）")
            return std_ET

    def _init_parser(self):
        """初始化解析器别名"""
        self.Element = self.ET.Element
        self.SubElement = self.ET.SubElement
        self.tostring = self.ET.tostring

    def parse(self, source):
        """
        解析 XML 源

        Args:
            source: 文件路径或文件对象

        Returns:
            元素树对象
        """
        return self.ET.parse(source)

    def fromstring(self, text):
        """
        从字符串解析 XML

        Args:
            text: XML 字符串

        Returns:
            根元素
        """
        # lxml 对带编码声明的 Unicode 字符串有特殊处理
        if LXML_AVAILABLE and self.ET is lxml_ET:
            if isinstance(text, str) and '<?xml' in text:
                # 对于带编码声明的 XML，lxml 更推荐使用 bytes
                text_bytes = text.encode('utf-8')
                return self.ET.fromstring(text_bytes)
        return self.ET.fromstring(text)

    def find(self, element, path, namespaces=None):
        """
        查找单个元素

        Args:
            element: 父元素
            path: XPath 路径
            namespaces: 命名空间

        Returns:
            找到的元素或 None
        """
        return element.find(path, namespaces)

    def findall(self, element, path, namespaces=None):
        """
        查找所有匹配的元素

        Args:
            element: 父元素
            path: XPath 路径
            namespaces: 命名空间

        Returns:
            找到的元素列表
        """
        return element.findall(path, namespaces)

    def get_text(self, element, default: str = "") -> str:
        """
        获取元素的文本内容

        Args:
            element: XML 元素
            default: 默认值

        Returns:
            文本内容，去除首尾空白
        """
        if element is not None and element.text is not None:
            return element.text.strip()
        return default

    def get_attribute(self, element, attr, default: str = "") -> str:
        """
        获取元素的属性值

        Args:
            element: XML 元素
            attr: 属性名
            default: 默认值

        Returns:
            属性值
        """
        if element is not None:
            return element.get(attr, default)
        return default

    def find_text(self, element, path, default: str = "") -> str:
        """
        查找元素并获取其文本内容

        Args:
            element: 父元素
            path: XPath 路径
            default: 默认值

        Returns:
            找到的文本
        """
        found = self.find(element, path)
        return self.get_text(found, default)

    def get_available_parsers(self) -> List[Dict[str, Any]]:
        """
        获取可用解析器列表

        Returns:
            解析器信息列表
        """
        parsers = []

        if LXML_AVAILABLE:
            parsers.append({
                'name': 'lxml',
                'priority': 10,
                'available': True,
                'description': '高性能 XML 解析器（推荐）',
                'features': ['XPath', 'XSLT', '验证', 'SAX', 'DOM']
            })

        if DEFUSEDXML_AVAILABLE:
            parsers.append({
                'name': 'defusedxml',
                'priority': 5,
                'available': True,
                'description': '安全 XML 解析器',
                'features': ['防止 XXE 攻击', '防止拒绝服务']
            })

        parsers.append({
            'name': 'std_xml',
            'priority': 1,
            'available': True,
            'description': '标准库 XML 解析器',
            'features': ['基础解析', '无依赖']
        })

        return parsers

    @property
    def current_parser(self) -> str:
        """获取当前解析器名称"""
        if LXML_AVAILABLE and self.ET is lxml_ET:
            return 'lxml'
        elif DEFUSEDXML_AVAILABLE and self.ET is defused_ET:
            return 'defusedxml'
        else:
            return 'std_xml'


# 全局解析器实例
_parser: Optional[XMLParser] = None


def get_parser(prefer_performance: bool = True) -> XMLParser:
    """
    获取全局 XML 解析器实例（单例模式）

    Args:
        prefer_performance: 是否优先选择性能

    Returns:
        XML 解析器实例
    """
    global _parser
    if _parser is None or _parser.prefer_performance != prefer_performance:
        _parser = XMLParser(prefer_performance)
    return _parser


# 快捷函数
def parse(source):
    """解析 XML 文件"""
    return get_parser().parse(source)


def fromstring(text):
    """从字符串解析 XML"""
    return get_parser().fromstring(text)


def find(element, path, namespaces=None):
    """查找单个元素"""
    return get_parser().find(element, path, namespaces)


def findall(element, path, namespaces=None):
    """查找所有元素"""
    return get_parser().findall(element, path, namespaces)


def get_text(element, default: str = "") -> str:
    """获取元素文本"""
    return get_parser().get_text(element, default)


def get_attribute(element, attr, default: str = "") -> str:
    """获取元素属性"""
    return get_parser().get_attribute(element, attr, default)


def find_text(element, path, default: str = "") -> str:
    """查找元素并获取文本"""
    return get_parser().find_text(element, path, default)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("XML 解析器测试")
    print("=" * 60)

    parser = XMLParser()
    print(f"\n当前解析器: {parser.current_parser}")

    print("\n可用解析器:")
    for p in parser.get_available_parsers():
        print(f"  - {p['name']}: {p['description']}")

    # 测试 XML 解析
    test_xml = """<?xml version="1.0" encoding="utf-8"?>
    <test>
        <title>测试标题</title>
        <content>测试内容</content>
        <item id="1">项目 1</item>
        <item id="2">项目 2</item>
    </test>
    """

    print("\n测试解析:")
    root = parser.fromstring(test_xml)
    title = parser.find_text(root, "title")
    print(f"  标题: {title}")

    items = parser.findall(root, "item")
    print(f"  找到 {len(items)} 个项目")
    for item in items:
        print(f"    - ID={parser.get_attribute(item, 'id')}")
        print(f"      内容: {parser.get_text(item)}")
