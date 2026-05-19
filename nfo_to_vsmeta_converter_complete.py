#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
NFO to VSMETA 转换器 - 完全版
================================================================================

【功能概述】
将 Kodi/XBMC 格式的 NFO 元数据文件转换为群晖 Video Station 的 VSMETA 格式。

【主要特性】
1. NFO 解析 - 支持 Kodi/XBMC 标准 XML 格式，自动提取影片元数据
2. VSMETA 生成 - 生成群晖 Video Station 兼容的二进制元数据文件
3. 并发处理 - 支持多线程/多进程模式，充分利用多核 CPU
4. 断点续传 - 支持中断后继续处理，避免重复工作
5. 智能重试 - 失败文件自动重试，支持配置重试次数和延迟
6. 图片压缩 - 自动压缩海报图片，支持配置大小和压缩比
7. 图片缓存 - LRU 缓存机制，避免重复压缩相同图片
8. 进度显示 - tqdm 进度条实时显示处理进度
9. 信号处理 - 支持 Ctrl+C 优雅退出，自动保存进度
10. 报告导出 - 支持 HTML/CSV/TXT 三种格式的转换报告

【使用方法】
命令行模式:
    python nfo_to_vsmeta_converter_complete.py -d /path/to/movies --workers 8

交互模式:
    python nfo_to_vsmeta_converter_complete.py -i

菜单模式:
    python nfo_to_vsmeta_converter_complete.py

【依赖库】
必需: 无（标准库即可运行）
可选:
    - Pillow: 图片压缩功能
    - tqdm: 进度条显示
    - colorama: 彩色终端输出
    - readchar: 上下键菜单选择

作者: AI Assistant
版本: 2.0.1
更新日期: 2024
================================================================================
"""

# ============================================================================
# 标准库导入
# ============================================================================

import argparse  # 命令行参数解析
import atexit  # 程序退出时的回调注册
import copy  # 对象深拷贝
import csv  # CSV 文件读写
import fnmatch  # 文件名通配符匹配
import html  # HTML 转义（防止 XSS）
import importlib.util  # 动态导入插件模块
import io  # 内存缓冲区操作
import itertools  # 迭代工具（用于动画）
import json  # JSON 配置文件读写
import logging  # 日志记录
from logging.handlers import RotatingFileHandler  # 日志文件轮转处理器
import os  # 操作系统接口

# import pickle 已移除，改用 json（安全修复）
import re  # 正则表达式
import shutil  # 文件操作（复制、移动等）
import hashlib  # 文件内容哈希（热重载检测）
import signal  # 信号处理（Ctrl+C）
import sys  # 系统相关功能
import threading  # 多线程支持
import time  # 时间相关功能
import xml.etree.ElementTree as ET  # XML 解析

# 并发处理相关
from abc import ABC, abstractmethod  # 抽象基类（插件系统）

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

# 数据类支持
from dataclasses import dataclass, field, asdict

# 日期时间处理
from datetime import datetime

# 类型注解
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path  # 路径处理

# ============================================================================
# 可选库导入（带优雅降级）
# ============================================================================

# tqdm 进度条 - 用于显示处理进度
try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Pillow 图片处理 - 用于图片压缩
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# colorama 彩色终端输出
try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)  # 自动重置颜色
    _HAS_COLORAMA = True
except ImportError:
    # 未安装时使用空字符串替代，保证代码正常运行
    class _Fore:
        """颜色常量的空实现（无 colorama 时的回退）"""

        CYAN = GREEN = YELLOW = RED = LIGHTMAGENTA_EX = ""
        LIGHTBLACK_EX = LIGHTYELLOW_EX = LIGHTCYAN_EX = LIGHTGREEN_EX = ""
        BRIGHT = ""

    class _Style:
        """样式常量的空实现"""

        RESET_ALL = BRIGHT = ""

    Fore = _Fore()
    Style = _Style()
    _HAS_COLORAMA = False

# Rich 终端增强库
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import (
        Progress,
        SpinnerColumn,
        BarColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
        MofNCompleteColumn,
    )
    from rich.logging import RichHandler
    from rich import box

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Rich Console 初始化
if HAS_RICH:
    console = Console()
else:
    console = None


# ============================================================================
# ANSI 颜色自动检测
# ============================================================================


def _should_use_color() -> bool:
    """检测是否应该使用 ANSI 颜色"""
    if not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return True


USE_COLOR = _should_use_color()

# 如果不应该使用颜色，覆盖 Fore 和 Style
if not USE_COLOR:

    class _NoColorFore:
        """无颜色输出的 Fore 替代类"""

        CYAN = GREEN = YELLOW = RED = LIGHTMAGENTA_EX = ""
        LIGHTBLACK_EX = LIGHTYELLOW_EX = LIGHTCYAN_EX = LIGHTGREEN_EX = ""
        BRIGHT = ""

    class _NoColorStyle:
        """无颜色输出的 Style 替代类"""

        RESET_ALL = BRIGHT = ""

    Fore = _NoColorFore()
    Style = _NoColorStyle()

# readchar 键盘输入 - 用于上下键菜单选择
try:
    import readchar

    HAS_READCHAR = True
except ImportError:
    HAS_READCHAR = False


# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型层
# ============================================================================


@dataclass
class VideoMetadata:
    """
    视频元数据结构

    存储从 NFO 文件解析出的所有影片信息，包括：
    - 基本信息：标题、年份、评分、剧情等
    - 人员信息：导演、演员、编剧等
    - 分类信息：类型、国家、语言等
    - 图片数据：海报、背景图的二进制数据
    - 剧集信息：季数、集数、剧集名称等

    使用 dataclass 装饰器自动生成 __init__、__repr__ 等方法。
    """

    # === 基本信息 ===
    title: str = ""  # 影片标题
    original_title: str = ""  # 原始标题（通常为原文标题）
    year: int = 0  # 上映年份
    rating: float = 0.0  # 评分（0-10）
    plot: str = ""  # 剧情简介
    tagline: str = ""  # 宣传语
    runtime: int = 0  # 时长（分钟）

    # === 分类列表 ===
    genres: List[str] = field(default_factory=list)  # 类型列表（如：动作、科幻）
    directors: List[str] = field(default_factory=list)  # 导演列表
    actors: List[str] = field(default_factory=list)  # 演员列表
    writers: List[str] = field(default_factory=list)  # 编剧列表
    studios: List[str] = field(default_factory=list)  # 制作公司列表
    countries: List[str] = field(default_factory=list)  # 国家/地区列表
    languages: List[str] = field(default_factory=list)  # 语言列表
    certifications: List[str] = field(default_factory=list)  # 分级列表

    # === 日期和链接 ===
    release_date: str = ""  # 上映日期

    # === 图片数据（二进制） ===
    poster_data: bytes = b""  # 海报图片数据
    poster_url: str = ""  # 海报图片 URL
    backdrop_data: bytes = b""  # 背景图片数据
    backdrop_url: str = ""  # 背景图片 URL
    trailer_url: str = ""  # 预告片 URL

    # === 外部 ID ===
    imdb_id: str = ""  # IMDb ID（如：tt1234567）
    tmdb_id: str = ""  # TMDB ID
    tvdb_id: str = ""  # TVDB ID

    # === 剧集专用字段 ===
    season: int = 0  # 季数
    episode: int = 0  # 集数
    episode_title: str = ""  # 单集标题
    series_name: str = ""  # 剧集名称
    episode_plot: str = ""  # 单集剧情


@dataclass
class Config:
    """
    配置类

    存储程序运行所需的所有配置项，支持：
    - 从 JSON 文件加载配置
    - 保存配置到 JSON 文件
    - 默认值自动填充

    配置项说明：
    - directory: 处理目录（支持多个目录）
    - file_include_patterns: 文件包含模式（通配符）
    - file_exclude_patterns: 文件排除模式（通配符）
    - file_regex: 文件名正则过滤
    - max_image_size_kb: 图片最大大小（KB）
    - image_compression_ratio: 图片压缩比例（0.1-1.0）
    - max_workers: 并发工作线程/进程数
    - retry_attempts: 失败重试次数
    - retry_delay: 重试延迟（秒）
    - process_mode: 处理模式（thread/process）
    """

    # === 目录配置 ===
    directory: Union[str, List[str]] = "."  # 处理目录，支持字符串或列表

    # === 文件过滤 ===
    file_include_patterns: Optional[List[str]] = None  # 包含模式，如 ["*.mkv", "*.mp4"]
    file_exclude_patterns: Optional[List[str]] = None  # 排除模式
    file_regex: Optional[str] = None  # 正则表达式过滤

    # === 图片设置 ===
    max_image_size_kb: int = 200  # 图片最大大小（KB）
    image_compression_ratio: float = 0.8  # JPEG 压缩质量比例

    # === 并发设置 ===
    max_workers: int = 4  # 最大并发数
    retry_attempts: int = 3  # 重试次数
    retry_delay: float = 1.0  # 重试延迟（秒），会递增
    log_level: str = "INFO"  # 日志级别
    process_mode: str = "thread"  # 处理模式: 'thread' 或 'process'

    # === 文件处理选项 ===
    overwrite_existing: bool = False  # 是否覆盖已存在的 VSMETA
    delete_existing_vsmeta: bool = False  # 是否删除已存在的 VSMETA
    enable_backup: bool = True  # 是否启用备份

    # === 大小过滤 ===
    min_size: int = 0  # 最小文件大小（字节）
    max_size: int = 0  # 最大文件大小（字节），0 表示不限制

    # === 路径配置 ===
    backup_dir: str = ".backup"  # 备份目录名
    checkpoint_file: str = "conversion_checkpoint.json"  # 断点文件名
    vsmeta_extension: str = ".vsmeta"  # VSMETA 文件扩展名

    # === 支持的文件扩展名 ===
    nfo_extensions: List[str] = field(default_factory=lambda: [".nfo"])
    video_extensions: List[str] = field(
        default_factory=lambda: [".mp4", ".mkv", ".avi", ".ts", ".wmv", ".rmvb", ".mov", ".m4v"]
    )

    # === AI 功能（预留） ===
    enable_ai_completion: bool = False  # 是否启用 AI 补全
    ai_api_key: str = ""  # AI API 密钥
    ai_api_url: str = ""  # AI API 地址

    # === 插件配置 ===
    plugin_dir: str = "plugins"  # 插件目录
    auto_load_plugins: bool = False  # 是否自动加载插件

    # === 预演模式 ===
    dry_run: bool = False  # 预演模式，不实际写入文件

    # === 报告输出配置 ===
    report_output_dir: str = ""  # 报告输出目录，为空则使用当前目录

    # === 输出格式配置 ===
    output_formats: List[str] = field(
        default_factory=lambda: ["vsmeta"]
    )  # 输出格式列表，支持 vsmeta 和 nfo

    # === 日志文件配置 ===
    log_file: str = ""  # 日志文件路径，为空则不写入文件
    log_file_max_size: int = 10 * 1024 * 1024  # 日志文件最大大小（10MB）
    log_file_backup_count: int = 5  # 日志文件备份数量

    # === 备份文件清理配置 ===
    backup_max_count: int = 5  # 每个文件最多保留的备份数量
    backup_max_age_days: int = 30  # 备份文件最大保留天数

    # === 剧集模式配置 ===
    tv_show_mode: bool = False  # 是否启用剧集模式

    # === 性能优化配置 ===
    image_cache_max_size: int = 50  # 图片缓存最大数量
    checkpoint_save_interval: int = 10  # 断点保存间隔（文件数）

    def __post_init__(self):
        """
        初始化后处理

        将单个目录字符串转换为列表，统一处理逻辑。
        """
        if isinstance(self.directory, str):
            self.directory = [self.directory]

        # 值域校验，防止非法配置值
        self.max_workers = max(1, min(32, self.max_workers))
        self.image_compression_ratio = max(0.1, min(1.0, self.image_compression_ratio))
        self.max_image_size_kb = max(10, self.max_image_size_kb)
        self.retry_attempts = max(0, min(20, self.retry_attempts))
        self.retry_delay = max(0.1, min(60, self.retry_delay))

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """
        从 JSON 文件加载配置

        Args:
            path: JSON 配置文件路径

        Returns:
            Config 对象

        Note:
            如果文件不存在或解析失败，返回默认配置
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"配置文件 {path} 加载失败: {e}，使用默认配置")
            return cls()

    def save_to_file(self, path: str):
        """
        保存配置到 JSON 文件

        Args:
            path: 保存路径
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


@dataclass
class ConversionStats:
    """
    转换统计信息

    记录转换过程中的各项统计数据，用于：
    - 实时显示处理进度
    - 生成转换报告
    - 性能分析

    属性说明：
    - start_time: 开始时间
    - end_time: 结束时间
    - total_files: 总文件数
    - processed_files: 已处理文件数
    - success_files: 成功文件数
    - failed_files: 失败文件数
    - skipped_files: 跳过文件数
    - errors: 错误详情列表
    """

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_files: int = 0
    processed_files: int = 0
    success_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    nfo_missing: int = 0
    errors: List[Dict] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """
        计算处理耗时（秒）

        Returns:
            从开始到结束（或当前）的秒数
        """
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """
        计算成功率（百分比）

        Returns:
            成功处理的文件占总处理文件的百分比
        """
        if self.processed_files == 0:
            return 0.0
        return (self.success_files / self.processed_files) * 100


# ============================================================================
# 进程模式工作函数（模块级纯函数，用于 ProcessPoolExecutor 序列化）
# ============================================================================


def _process_file_worker(args: Tuple) -> Dict:
    """
    进程模式的工作函数（必须是模块级纯函数才能被 pickle）

    用于 ProcessPoolExecutor 并发处理，避免绑定方法序列化问题。

    Args:
        args: 元组，包含 (directory, filename, config_dict)
            - directory: 目录路径
            - filename: 文件名
            - config_dict: Config 对象的字典表示

    Returns:
        处理结果字典，包含:
            - success: 是否成功
            - result: 结果类型（success/skipped/nfo_missing/parse_error/generate_error/write_error）
            - error: 错误信息（如有）
    """
    directory, filename, config_dict = args

    # 重建必要的对象
    config = Config(**config_dict)
    parser = NFOParser(config)
    generator = VSMETAGenerator(config)

    # 简化的处理逻辑（参考 _process_single_file）
    filepath = os.path.join(directory, filename)
    base_name = os.path.splitext(filename)[0]
    nfo_path = os.path.join(directory, base_name + ".nfo")
    vsmeta_path = filepath + config.vsmeta_extension

    # 检查 NFO 文件是否存在
    if not os.path.exists(nfo_path):
        return {"success": False, "result": "nfo_missing", "error": "NFO 文件不存在"}

    # 检查是否需要跳过已存在的 VSMETA
    if os.path.exists(vsmeta_path) and not config.overwrite_existing:
        return {"success": True, "result": "skipped", "error": "VSMETA 已存在"}

    # 解析 NFO 文件
    metadata = parser.parse(nfo_path)
    if metadata is None:
        return {"success": False, "result": "parse_error", "error": "NFO 解析失败"}

    # 生成 VSMETA 数据
    vsmeta_data = generator.generate(metadata)

    if len(vsmeta_data) == 0:
        return {"success": False, "result": "generate_error", "error": "VSMETA 生成失败"}

    # 写入文件
    try:
        with open(vsmeta_path, "wb") as f:
            f.write(vsmeta_data)
    except Exception as e:
        return {"success": False, "result": "write_error", "error": f"写入失败: {e}"}

    return {"success": True, "result": "success"}


# ============================================================================
# NFO 解析器
# ============================================================================


class NFOParser:
    """
    NFO 文件解析器

    负责解析 Kodi/XBMC 格式的 NFO XML 文件，提取影片元数据。

    支持的 NFO 格式：
    - Kodi 标准格式
    - XBMC 格式
    - 大多数媒体中心软件导出的 NFO

    解析流程：
    1. 读取并解析 XML 文件
    2. 根据字段映射提取元数据
    3. 处理列表类型字段（演员、类型等）
    4. 加载同目录下的海报图片
    """

    # Kodi/XBMC 标准字段映射
    # 键：VideoMetadata 字段名
    # 值：NFO 中可能的 XML 标签名列表（按优先级排序）
    FIELD_MAPPINGS = {
        "title": ["title", "localtitle", "originaltitle"],
        "original_title": ["originaltitle", "sorttitle"],
        "year": ["year", "premiered", "releasedate"],
        "rating": ["rating", "userrating"],
        "plot": ["plot", "outline"],
        "tagline": ["tagline"],
        "runtime": ["runtime", "duration"],
        "genres": ["genre", "genres"],
        "directors": ["director", "directors"],
        "actors": ["actor", "actors", "cast"],
        "writers": ["credits", "writer", "writers"],
        "studios": ["studio", "studios"],
        "countries": ["country", "countries"],
        "languages": ["language", "languages"],
        "certifications": ["mpaa", "certification", "certifications"],
        "release_date": ["premiered", "releasedate", "dateadded"],
        "poster_url": ["thumb", "poster", "fanart"],
        "backdrop_url": ["fanart", "backdrop"],
        "trailer_url": ["trailer"],
        "imdb_id": ["imdb", "imdbid", "id"],
        "tmdb_id": ["tmdbid", "tmdb"],
        "tvdb_id": ["tvdbid", "tvdb"],
        "season": ["season"],
        "episode": ["episode"],
        "episode_title": ["episodetitle", "showtitle"],
        "series_name": ["showtitle", "series"],
        "episode_plot": ["episodeplot", "episodesummary"],
    }

    def __init__(self, config: Config):
        """
        初始化解析器

        Args:
            config: 配置对象
        """
        self.config = config

    def parse(self, nfo_path: str) -> Optional[VideoMetadata]:
        """
        解析 NFO 文件

        Args:
            nfo_path: NFO 文件路径

        Returns:
            VideoMetadata 对象，解析失败返回 None
        """
        try:
            # === 先读取文件内容，检测编码 ===
            with open(nfo_path, "rb") as f:
                raw_data = f.read()

            # === 检测编码 ===
            try:
                # 尝试 UTF-8（优先处理 BOM）
                if raw_data.startswith(b"\xef\xbb\xbf"):  # UTF-8 BOM
                    content = raw_data[3:].decode("utf-8")
                else:
                    try:
                        content = raw_data.decode("utf-8")
                    except UnicodeDecodeError:
                        # 尝试 GBK/GB2312（常见于中文 NFO）
                        try:
                            content = raw_data.decode("gbk")
                        except UnicodeDecodeError:
                            # 最后尝试 Latin-1（不会失败）
                            content = raw_data.decode("latin-1")
            except Exception as e:
                logger.error(f"读取 NFO 文件失败 {nfo_path}: {e}")
                return None

            # === 从字符串解析 XML ===
            # 使用 defusedxml 防止 XML 外部实体（XXE）攻击
            try:
                from defusedxml import ElementTree as DefusedET

                root = DefusedET.fromstring(content)
            except ImportError:
                # 如果 defusedxml 未安装，使用标准库并禁用实体处理
                logger.warning("defusedxml 未安装，使用标准库 XML 解析（安全性降低）")
                parser = ET.XMLParser()
                parser.entity = {}
                root = ET.fromstring(content, parser=parser)
            return self._extract_metadata(root, nfo_path)
        except ET.ParseError as e:
            logger.error(f"解析 NFO 文件失败 {nfo_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"读取 NFO 文件失败 {nfo_path}: {e}")
            return None

    def _extract_metadata(self, root: ET.Element, nfo_path: str) -> VideoMetadata:
        """
        从 XML 根元素提取元数据

        Args:
            root: XML 根元素
            nfo_path: NFO 文件路径（用于加载海报）

        Returns:
            填充后的 VideoMetadata 对象
        """
        metadata = VideoMetadata()

        # === 提取基本字段 ===
        # 遍历字段映射，按优先级查找第一个匹配的标签
        for field_name, tags in self.FIELD_MAPPINGS.items():
            for tag in tags:
                elem = root.find(f".//{tag}")
                if elem is not None and elem.text:
                    value = elem.text.strip()
                    self._set_field(metadata, field_name, value)
                    break

        # === 处理列表字段 ===
        # 这些字段可能有多个值，需要特殊处理
        metadata.genres = self._extract_list(root, ["genre"])
        metadata.directors = self._extract_list(root, ["director"])
        metadata.writers = self._extract_list(root, ["credits"])
        metadata.studios = self._extract_list(root, ["studio"])
        metadata.countries = self._extract_list(root, ["country"])
        metadata.languages = self._extract_list(root, ["language"])

        # === 处理演员列表 ===
        # 演员信息在 <actor><name> 标签中
        metadata.actors = self._extract_actors(root)

        # === 加载海报图片 ===
        metadata.poster_data = self._load_poster(nfo_path)

        # === 后处理：从日期提取年份 ===
        if metadata.year == 0 and metadata.release_date:
            year_match = re.search(r"(\d{4})", metadata.release_date)
            if year_match:
                metadata.year = int(year_match.group(1))

        # === 后处理：清理时长字符串 ===
        if isinstance(metadata.runtime, str):
            runtime_match = re.search(r"(\d+)", str(metadata.runtime))
            if runtime_match:
                metadata.runtime = int(runtime_match.group(1))

        # === 后处理：自动检测剧集模式 ===
        # 如果 NFO 中没有季/集信息，尝试从目录和文件名推断
        if metadata.season == 0 or metadata.episode == 0:
            directory = os.path.dirname(nfo_path)
            filename = os.path.basename(nfo_path)
            is_tv_show, show_name = self.detect_tv_show_mode(directory, filename)
            if is_tv_show:
                # 从文件名提取季集信息
                ep_match = re.search(r"[Ss](\d+)[Ee](\d+)", filename)
                if not ep_match:
                    ep_match = re.search(r"(\d+)[xX](\d+)", filename)
                if ep_match:
                    if metadata.season == 0:
                        metadata.season = int(ep_match.group(1))
                    if metadata.episode == 0:
                        metadata.episode = int(ep_match.group(2))
                # 填充剧集名称
                if show_name and not metadata.series_name:
                    metadata.series_name = show_name

        return metadata

    def _set_field(self, metadata: VideoMetadata, field: str, value: str):
        """
        设置元数据字段（带类型转换）

        Args:
            metadata: 元数据对象
            field: 字段名
            value: 字符串值
        """
        # 整数字段
        if field in ["year", "season", "episode", "runtime"]:
            try:
                setattr(metadata, field, int(value))
            except ValueError:
                pass
        # 浮点字段
        elif field == "rating":
            try:
                setattr(metadata, field, float(value))
            except ValueError:
                pass
        # 字符串字段
        else:
            setattr(metadata, field, value)

    def _extract_list(self, root: ET.Element, tags: List[str]) -> List[str]:
        """
        提取列表类型的字段

        Args:
            root: XML 根元素
            tags: 标签名列表

        Returns:
            去重后的字符串列表
        """
        result = []
        for tag in tags:
            for elem in root.findall(f".//{tag}"):
                if elem.text:
                    result.append(elem.text.strip())
        # 使用 dict.fromkeys 保持顺序去重
        return list(dict.fromkeys(result))

    def _extract_actors(self, root: ET.Element) -> List[str]:
        """
        提取演员列表

        演员信息格式：
        <actor>
            <name>演员名</name>
            <role>角色名</role>
        </actor>

        Args:
            root: XML 根元素

        Returns:
            演员名称列表
        """
        actors = []
        for actor in root.findall(".//actor"):
            name = actor.find("name")
            if name is not None and name.text:
                actors.append(name.text.strip())
        return actors

    def _safe_read_image(self, path: str) -> Optional[bytes]:
        """安全读取图片文件"""
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"读取海报失败 {path}: {e}")
            return None

    def _load_poster(self, nfo_path: str) -> bytes:
        """
        加载同目录下的海报图片

        查找顺序：
        1. 视频文件名-poster.jpg/png
        2. 视频文件名-thumb.jpg/png
        3. 视频文件名.poster.jpg/png
        4. 视频文件名.jpg/png（同名）
        5. 目录下的 poster.*、cover.*、folder.* 文件

        Args:
            nfo_path: NFO 文件路径

        Returns:
            图片二进制数据，未找到返回空字节
        """
        base_path = os.path.splitext(nfo_path)[0]
        poster_names = ["-poster", "-thumb", ".poster", ".thumb", "-fanart", ""]
        extensions = [".jpg", ".jpeg", ".png", ".webp"]

        # === 查找同名海报 ===
        for name in poster_names:
            for ext in extensions:
                poster_path = f"{base_path}{name}{ext}"
                if os.path.exists(poster_path):
                    data = self._safe_read_image(poster_path)
                    if data:
                        return data

        # === 查找目录下的通用海报文件 ===
        dir_path = os.path.dirname(nfo_path)
        try:
            dir_listing = os.listdir(dir_path)
        except OSError as e:
            logger.warning(f"无法读取目录 {dir_path}: {e}")
            return b""

        for filename in dir_listing:
            if filename.lower().startswith(("poster", "cover", "folder", "default")):
                ext = os.path.splitext(filename)[1].lower()
                if ext in extensions:
                    poster_path = os.path.join(dir_path, filename)
                    data = self._safe_read_image(poster_path)
                    if data:
                        return data

        return b""

    def detect_tv_show_mode(self, directory: str, filename: str) -> Tuple[bool, str]:
        """
        检测是否为剧集模式

        Args:
            directory: 文件所在目录
            filename: 文件名

        Returns:
            (是否剧集模式, 剧集名称)
        """
        # 检查目录结构：Show Name/Season XX/
        parts = Path(directory).parts
        season_match = None
        show_name = ""

        for i, part in enumerate(reversed(parts)):
            match = re.match(r"[Ss]eason\s*(\d+)", part)
            if match:
                season_match = int(match.group(1))
                if i + 1 < len(parts):
                    show_name = parts[-(i + 2)]
                break

        # 检查文件名：S01E02 或 1x02 格式
        ep_match = re.search(r"[Ss](\d+)[Ee](\d+)", filename)
        if not ep_match:
            ep_match = re.search(r"(\d+)[xX](\d+)", filename)

        is_tv_show = bool(season_match or ep_match)
        return is_tv_show, show_name


# ============================================================================
# VSMETA 生成器
# ============================================================================


class ImageCache:
    """
    图片压缩缓存（LRU 策略）

    功能：
    - 缓存已压缩的图片，避免重复压缩
    - 基于文件路径 + 修改时间生成缓存键
    - LRU（最近最少使用）淘汰策略

    使用场景：
    同一目录下的多个视频文件可能共享同一张海报图片，
    使用缓存可以避免对同一张图片重复压缩。
    """

    def __init__(self, max_size: int = 100):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
        """
        self._cache: OrderedDict[str, bytes] = OrderedDict()  # 有序字典缓存（LRU）
        self._max_size = max_size  # 最大容量
        self._lock = threading.Lock()  # 线程锁

    def _get_cache_key(self, image_path: str) -> str:
        """
        生成缓存键

        使用文件路径 + 修改时间作为键，确保文件更新后缓存失效。

        Args:
            image_path: 图片文件路径

        Returns:
            缓存键字符串
        """
        try:
            mtime = os.path.getmtime(image_path)
            return f"{image_path}:{mtime}"
        except OSError:
            return image_path

    def get(self, image_path: str) -> Optional[bytes]:
        """
        获取缓存的图片数据

        Args:
            image_path: 图片文件路径

        Returns:
            缓存的图片数据，未命中返回 None
        """
        key = self._get_cache_key(image_path)
        with self._lock:
            if key in self._cache:
                # 更新访问顺序（移到末尾表示最近使用）
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, image_path: str, data: bytes):
        """
        添加图片数据到缓存

        如果缓存已满，淘汰最久未使用的条目。

        Args:
            image_path: 图片文件路径
            data: 压缩后的图片数据
        """
        key = self._get_cache_key(image_path)
        with self._lock:
            # LRU 淘汰：移除最久未访问的条目（有序字典头部）
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            self._cache[key] = data
            self._cache.move_to_end(key)

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()


class VSMETAGenerator:
    """
    VSMETA 文件生成器

    负责将 VideoMetadata 对象转换为群晖 Video Station 的 VSMETA 二进制格式。

    VSMETA 格式说明：
    - 群晖专有的二进制元数据格式
    - 使用变长整数（varint）编码
    - 字符串使用 UTF-8 编码，前缀长度
    - 包含影片信息和海报图片

    二进制结构（简化）：
    [版本] [标题] [原标题] [剧情] [宣传语] [年份] [评分] [时长]
    [类型列表] [导演列表] [演员列表] [编剧列表]
    [海报数据] [背景数据] [IMDB ID] [TMDB ID] [上映日期]
    [季数] [集数] [剧集标题] [剧集名称]
    """

    # VSMETA 格式常量
    VSMETA_VERSION = 1  # 格式版本号
    VSMETA_MAGIC = b"\x08\x01"  # 魔数（格式标识）

    def __init__(self, config: Config):
        """
        初始化生成器

        Args:
            config: 配置对象
        """
        self.config = config
        self._image_cache = ImageCache(
            max_size=getattr(config, "image_cache_max_size", 50)
        )  # 使用配置的缓存大小

    def generate(self, metadata: VideoMetadata) -> bytes:
        """
        生成 VSMETA 二进制数据

        Args:
            metadata: 视频元数据对象

        Returns:
            VSMETA 格式的二进制数据
        """
        parts = []

        # === 版本信息 ===
        parts.append(self._write_varint(self.VSMETA_VERSION))

        # === 基本信息 ===
        parts.append(self._write_string(metadata.title))
        parts.append(self._write_string(metadata.original_title))
        parts.append(self._write_string(metadata.plot))
        parts.append(self._write_string(metadata.tagline))

        # === 数字字段 ===
        parts.append(self._write_varint(metadata.year))
        parts.append(self._write_varint(int(metadata.rating * 10)))  # 评分放大 10 倍存储
        parts.append(self._write_varint(metadata.runtime))

        # === 列表字段 ===
        parts.append(self._write_string_list(metadata.genres))
        parts.append(self._write_string_list(metadata.directors))
        parts.append(self._write_string_list(metadata.actors))
        parts.append(self._write_string_list(metadata.writers))

        # === 图片数据 ===
        poster_compressed = self._compress_image(metadata.poster_data)
        parts.append(self._write_bytes(poster_compressed))

        backdrop_compressed = self._compress_image(metadata.backdrop_data)
        parts.append(self._write_bytes(backdrop_compressed))

        # === 额外信息 ===
        parts.append(self._write_string(metadata.imdb_id))
        parts.append(self._write_string(metadata.tmdb_id))
        parts.append(self._write_string(metadata.release_date))

        # === 剧集信息 ===
        parts.append(self._write_varint(metadata.season))
        parts.append(self._write_varint(metadata.episode))
        parts.append(self._write_string(metadata.episode_title))
        parts.append(self._write_string(metadata.series_name))

        return b"".join(parts)

    def _write_varint(self, value: int) -> bytes:
        """
        写入变长整数

        类似 Protocol Buffers 的 varint 编码：
        - 每个字节的低 7 位存储数据
        - 最高位表示是否还有后续字节

        Args:
            value: 整数值

        Returns:
            编码后的字节序列
        """
        if value < 0:
            raise ValueError(f"varint 不支持负数: {value}")
        if value == 0:
            return b"\x00"

        result = []
        while value > 0:
            byte = value & 0x7F  # 取低 7 位
            value >>= 7  # 右移 7 位
            if value > 0:
                byte |= 0x80  # 设置继续标志
            result.append(byte)

        return bytes(result)

    def _write_string(self, s: str) -> bytes:
        """
        写入字符串

        格式：[长度(varint)] [UTF-8 编码的字符串]

        Args:
            s: 字符串

        Returns:
            编码后的字节序列
        """
        if not s:
            return b"\x00"

        encoded = s.encode("utf-8")
        length_bytes = self._write_varint(len(encoded))
        return length_bytes + encoded

    def _write_bytes(self, data: bytes) -> bytes:
        """
        写入字节数组

        格式：[长度(varint)] [数据]

        Args:
            data: 字节数据

        Returns:
            编码后的字节序列
        """
        if not data:
            return b"\x00"

        length_bytes = self._write_varint(len(data))
        return length_bytes + data

    def _write_string_list(self, items: List[str]) -> bytes:
        """
        写入字符串列表

        格式：[数量(varint)] [字符串1] [字符串2] ...

        Args:
            items: 字符串列表

        Returns:
            编码后的字节序列
        """
        if not items:
            return b"\x00"

        parts = [self._write_varint(len(items))]
        for item in items:
            parts.append(self._write_string(item))

        return b"".join(parts)

    def _compress_image(self, image_data: bytes, image_path: str = "") -> bytes:
        """
        压缩图片到指定大小

        压缩策略：
        1. 检查缓存，命中则直接返回
        2. 检查原图大小，符合要求则直接返回
        3. 逐步降低 JPEG 质量
        4. 如果仍不符合，缩小图片尺寸
        5. 存入缓存

        Args:
            image_data: 原始图片数据
            image_path: 图片路径（用于缓存键）

        Returns:
            压缩后的图片数据
        """
        if not image_data:
            return b""

        # === 尝试从缓存获取 ===
        if image_path:
            cached = self._image_cache.get(image_path)
            if cached is not None:
                logger.debug(f"图片缓存命中: {image_path}")
                return cached

        # === 无 PIL 时的处理 ===
        if not HAS_PIL:
            max_size = self.config.max_image_size_kb * 1024
            if len(image_data) <= max_size:
                return image_data
            logger.warning("PIL 未安装，无法压缩图片")
            return image_data

        try:
            img = Image.open(io.BytesIO(image_data))

            # 处理所有非 RGB 模式
            if img.mode not in ("RGB", "L"):
                if img.mode in ("RGBA", "LA"):
                    # 带 alpha 通道：创建白色背景
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[3])
                    else:
                        background.paste(img, mask=img.split()[1])
                    img = background
                elif img.mode == "P":
                    img = img.convert("RGB")
                elif img.mode == "CMYK":
                    img = img.convert("RGB")
                elif img.mode == "1":
                    img = img.convert("RGB")
                elif img.mode == "L":
                    img = img.convert("RGB")
                else:
                    # 其他模式尝试直接转换
                    try:
                        img = img.convert("RGB")
                    except Exception:
                        logger.warning(f"不支持的图片模式: {img.mode}")
                        return image_data
            elif img.mode == "L":
                # 灰度图转换为 RGB
                img = img.convert("RGB")

            max_size_kb = self.config.max_image_size_kb
            quality = int(self.config.image_compression_ratio * 100)

            # === 逐步降低质量直到满足大小要求 ===
            for attempt in range(5):
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=quality, optimize=True)
                compressed = output.getvalue()

                if len(compressed) <= max_size_kb * 1024:
                    # 存入缓存
                    if image_path:
                        self._image_cache.put(image_path, compressed)
                    return compressed

                # 降低质量和尺寸
                quality = max(quality - 10, 30)
                new_size = (int(img.width * 0.8), int(img.height * 0.8))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # === 最后一次尝试 ===
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=30, optimize=True)
            compressed = output.getvalue()

            if image_path:
                self._image_cache.put(image_path, compressed)
            return compressed

        except Exception as e:
            logger.warning(f"图片压缩失败: {e}")
            return image_data


# ============================================================================
# 文件扫描器
# ============================================================================


class FileScanner:
    """
    文件扫描器

    负责扫描指定目录，找出所有需要处理的视频文件。

    功能：
    - 递归扫描目录
    - 按扩展名过滤视频文件
    - 按大小过滤文件
    - 按通配符/正则过滤文件名
    - 排除备份目录
    """

    def __init__(self, config: Config):
        """
        初始化扫描器

        Args:
            config: 配置对象
        """
        self.config = config

    def scan(self) -> List[Tuple[str, str]]:
        """
        扫描目录，返回视频文件列表

        Returns:
            元组列表：[(目录路径, 文件名), ...]
        """
        results = []

        for directory in self.config.directory:
            if not os.path.isdir(directory):
                logger.warning(f"目录不存在: {directory}")
                continue

            results.extend(self._scan_directory(directory))

        return results

    def _scan_directory(self, directory: str) -> List[Tuple[str, str]]:
        """
        扫描单个目录

        Args:
            directory: 目录路径

        Returns:
            元组列表：[(目录路径, 文件名), ...]
        """
        results = []

        for root, dirs, files in os.walk(directory):
            # 排除备份目录
            if self.config.backup_dir in root:
                continue

            for filename in files:
                # 检查是否是视频文件
                if not self._is_video_file(filename):
                    continue

                # 检查文件大小
                filepath = os.path.join(root, filename)
                try:
                    file_size = os.path.getsize(filepath)
                    if self.config.min_size > 0 and file_size < self.config.min_size:
                        continue
                    if self.config.max_size > 0 and file_size > self.config.max_size:
                        continue
                except OSError:
                    continue

                # 检查文件名匹配
                if not self._matches_filters(filename):
                    continue

                results.append((root, filename))

        return results

    def _is_video_file(self, filename: str) -> bool:
        """
        检查是否是视频文件

        Args:
            filename: 文件名

        Returns:
            是否是视频文件
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.config.video_extensions

    def _matches_filters(self, filename: str) -> bool:
        """
        检查文件名是否匹配过滤规则

        过滤顺序：
        1. 包含模式（通配符）
        2. 排除模式（通配符）
        3. 正则表达式

        Args:
            filename: 文件名

        Returns:
            是否匹配所有过滤规则
        """
        # 通配符包含模式
        if self.config.file_include_patterns:
            matched = any(
                fnmatch.fnmatch(filename, pattern) for pattern in self.config.file_include_patterns
            )
            if not matched:
                return False

        # 通配符排除模式
        if self.config.file_exclude_patterns:
            excluded = any(
                fnmatch.fnmatch(filename, pattern) for pattern in self.config.file_exclude_patterns
            )
            if excluded:
                return False

        # 正则表达式
        if self.config.file_regex:
            if not re.search(self.config.file_regex, filename):
                return False

        return True


# ============================================================================
# 断点续传管理器
# ============================================================================


class CheckpointManager:
    """
    断点续传管理器（支持批量保存）

    功能：
    - 记录已处理和失败的文件
    - 支持中断后继续处理
    - 批量保存减少 IO 操作
    - 线程安全

    优化：
    - 使用待保存队列，批量写入
    - 使用临时文件+重命名，防止写入中断损坏
    - 每 N 个文件保存一次（可配置）
    """

    def __init__(self, checkpoint_file: str, save_interval: int = 10):
        """
        初始化断点管理器

        Args:
            checkpoint_file: 断点文件路径
            save_interval: 保存间隔（处理多少文件后保存）
        """
        self.checkpoint_file = checkpoint_file
        self.save_interval = save_interval
        self.completed: set = set()  # 已完成的文件
        self.failed: Dict[str, str] = {}  # 失败的文件及原因
        self._pending_completed: set = set()  # 待保存的已完成
        self._pending_failed: Dict[str, str] = {}  # 待保存的失败
        self._counter = 0  # 计数器
        self._lock = threading.Lock()  # 线程锁
        self._shutdown = False  # 关闭标志
        self.load()

    def load(self):
        """
        加载断点文件

        从 JSON 文件恢复之前的处理状态。
        """
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed = set(data.get("completed", []))
                    self.failed = data.get("failed", {})
                logger.info(
                    f"已加载断点文件，已完成: {len(self.completed)}, 失败: {len(self.failed)}"
                )
            except Exception as e:
                logger.warning(f"加载断点文件失败: {e}")
                self.completed = set()
                self.failed = {}

    def save(self, force: bool = False):
        """
        保存断点文件

        使用批量保存策略，减少 IO 操作。

        Args:
            force: 是否强制保存（忽略计数器）
        """
        with self._lock:
            # 检查是否需要保存
            if not force and self._counter < self.save_interval:
                return

            # 合并待保存数据
            self.completed.update(self._pending_completed)
            self.failed.update(self._pending_failed)
            self._pending_completed.clear()
            self._pending_failed.clear()
            self._counter = 0

            if self._shutdown:
                return

        try:
            data = {
                "completed": list(self.completed),
                "failed": self.failed,
                "timestamp": datetime.now().isoformat(),
            }
            # 原子写入：先写临时文件，再重命名（使用 JSON 格式）
            temp_file = self.checkpoint_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(temp_file, self.checkpoint_file)
        except Exception as e:
            logger.error(f"保存断点文件失败: {e}")

    def is_completed(self, filepath: str) -> bool:
        """
        检查文件是否已处理完成

        Args:
            filepath: 文件路径

        Returns:
            是否已完成
        """
        return filepath in self.completed or filepath in self._pending_completed

    def is_failed(self, filepath: str) -> bool:
        """
        检查文件是否处理失败

        Args:
            filepath: 文件路径

        Returns:
            是否失败
        """
        return filepath in self.failed or filepath in self._pending_failed

    def mark_completed(self, filepath: str):
        """
        标记文件为已完成

        Args:
            filepath: 文件路径
        """
        with self._lock:
            self._pending_completed.add(filepath)
            if filepath in self._pending_failed:
                del self._pending_failed[filepath]
            self._counter += 1
        self.save()

    def mark_failed(self, filepath: str, error: str):
        """
        标记文件为失败

        Args:
            filepath: 文件路径
            error: 错误信息
        """
        with self._lock:
            self._pending_failed[filepath] = error
            self._counter += 1
        self.save()

    def force_save(self):
        """强制立即保存"""
        self.save(force=True)

    def shutdown(self):
        """关闭时保存所有数据"""
        self._shutdown = True
        self.force_save()

    def clear(self):
        """清除所有断点"""
        with self._lock:
            self.completed.clear()
            self.failed.clear()
            self._pending_completed.clear()
            self._pending_failed.clear()
            self._counter = 0
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)


# ============================================================================
# 插件系统
# ============================================================================


class Plugin(ABC):
    """
    所有插件的基类

    插件是扩展转换器功能的模块，可以通过继承此基类来创建自定义插件。
    每个插件必须提供名称、版本和描述信息。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称（唯一标识）"""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本号"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """插件功能描述"""
        ...

    def on_register(self, config: "Config", plugin_config=None) -> None:
        """
        注册时回调，可读取配置

        Args:
            config: 当前配置对象
            plugin_config: 插件专属配置对象（PluginConfig 实例），可能为 None
        """
        pass

    def on_unregister(self) -> None:
        """注销时回调，用于清理资源"""
        pass

    @property
    def dependencies(self) -> List[str]:
        """必需依赖的插件名称列表，这些插件必须在当前插件之前加载"""
        return []

    @property
    def optional_dependencies(self) -> List[str]:
        """可选依赖的插件名称列表，如果存在则先加载，不存在也不报错"""
        return []

    @property
    def priority(self) -> int:
        """插件优先级，范围 0-100，默认 50，数字越大优先级越高，越先执行"""
        return 50

    @property
    def config_schema(self) -> Dict[str, Any]:
        """
        定义配置项的 schema，用于 WebUI 自动生成配置表单。
        支持类型: string, int, float, bool, list, dict
        返回格式: {"key": {"type": "string", "default": "", "description": "...", "min": 0, "max": 100}}
        """
        return {}


def plugin_priority(value: int):
    """设置插件优先级的装饰器，value 范围 0-100"""
    if not isinstance(value, int):
        raise TypeError(f"priority 必须是整数，收到 {type(value).__name__}")
    if not 0 <= value <= 100:
        raise ValueError(f"priority 范围 0-100，收到 {value}")

    def decorator(cls):
        @property
        def priority_fn(self):
            return getattr(self, "_plugin_priority", value)

        cls.priority = priority_fn
        return cls

    return decorator


class NFOParserPlugin(Plugin):
    """
    自定义 NFO 解析插件

    在默认解析完成后调用，可修改或补充元数据。
    """

    @abstractmethod
    def parse(self, nfo_path: str, metadata: VideoMetadata) -> Optional[VideoMetadata]:
        """
        解析/修改 NFO 元数据

        Args:
            nfo_path: NFO 文件路径
            metadata: 默认解析器已解析的元数据

        Returns:
            修改后的元数据，返回 None 表示跳过此插件的处理
        """
        ...


class VSMETAGeneratorPlugin(Plugin):
    """
    自定义 VSMETA 生成插件

    在默认生成完成后调用，可修改二进制数据。
    """

    @abstractmethod
    def generate(self, metadata: VideoMetadata, vsmeta_data: bytes) -> bytes:
        """
        修改 VSMETA 二进制数据

        Args:
            metadata: 视频元数据
            vsmeta_data: 默认生成器已生成的 VSMETA 二进制数据

        Returns:
            修改后的 VSMETA 二进制数据
        """
        ...


class MetadataEnhancerPlugin(Plugin):
    """
    元数据增强插件

    在 NFO 解析后、VSMETA 生成前调用，可从外部源补充数据。
    """

    @abstractmethod
    def enhance(self, metadata: VideoMetadata, filepath: str) -> VideoMetadata:
        """
        增强元数据

        Args:
            metadata: 当前元数据
            filepath: 对应的视频文件路径

        Returns:
            增强后的元数据
        """
        ...


class FileFilterPlugin(Plugin):
    """
    文件过滤插件

    在文件扫描后调用，可自定义过滤逻辑。
    """

    @abstractmethod
    def should_process(self, filepath: str, filename: str) -> bool:
        """
        判断文件是否应该被处理

        Args:
            filepath: 文件完整路径
            filename: 文件名

        Returns:
            True 表示应该处理，False 表示跳过
        """
        ...


class LifecyclePlugin(Plugin):
    """
    生命周期钩子插件

    在转换流程的各个阶段触发回调。
    """

    def on_start(self, config: Config) -> None:
        """
        转换开始时回调

        Args:
            config: 当前配置对象
        """
        pass

    def on_file_start(self, filepath: str) -> None:
        """
        单个文件开始处理时回调

        Args:
            filepath: 文件完整路径
        """
        pass

    def on_file_end(self, filepath: str, result: Dict) -> None:
        """
        单个文件处理结束时回调

        Args:
            filepath: 文件完整路径
            result: 处理结果字典
        """
        pass

    def on_finish(self, stats: ConversionStats) -> None:
        """
        转换全部完成时回调

        Args:
            stats: 转换统计信息
        """
        pass


# ============================================================================
# 插件配置管理
# ============================================================================


@dataclass
class PluginConfig:
    """
    插件配置管理类

    为每个插件提供独立的配置存储，支持持久化到 JSON 文件。
    配置文件存储在 plugins/configs/<plugin_name>.json
    """

    plugin_name: str
    config_dir: str = "plugins/configs"
    _data: Dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """初始化时加载已有配置"""
        self._ensure_config_dir()
        self._load()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        os.makedirs(self.config_dir, exist_ok=True)

    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        safe_name = "".join(c for c in self.plugin_name if c.isalnum() or c in "_-").lower()
        return os.path.join(self.config_dir, f"{safe_name}.json")

    def _load(self) -> None:
        """从文件加载配置"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.debug(f"已加载插件 '{self.plugin_name}' 的配置")
            except Exception as e:
                logger.warning(f"加载插件 '{self.plugin_name}' 配置失败: {e}")
                self._data = {}

    def _save(self) -> None:
        """保存配置到文件"""
        config_path = self._get_config_path()
        try:
            self._ensure_config_dir()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            logger.debug(f"已保存插件 '{self.plugin_name}' 的配置")
        except Exception as e:
            logger.error(f"保存插件 '{self.plugin_name}' 配置失败: {e}")

    def get(self, key: str, default=None):
        """
        获取配置项

        Args:
            key: 配置项名称
            default: 默认值

        Returns:
            配置值或默认值
        """
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """
        设置配置项并立即保存

        Args:
            key: 配置项名称
            value: 配置值
        """
        self._data[key] = value
        self._save()

    def update(self, values: Dict) -> None:
        """
        批量更新配置并保存

        Args:
            values: 配置字典
        """
        self._data.update(values)
        self._save()

    def get_all(self) -> Dict:
        """获取所有配置的副本"""
        return self._data.copy()

    def reset(self) -> None:
        """重置配置为空并保存"""
        self._data = {}
        self._save()


class PluginManager:
    """
    插件管理器

    负责插件的注册、注销、分类管理和调用。
    支持从目录动态加载插件文件。
    """

    def __init__(self):
        """初始化插件管理器"""
        self._plugins: Dict[str, Plugin] = {}  # name -> plugin 实例
        self._parser_plugins: List[NFOParserPlugin] = []
        self._generator_plugins: List[VSMETAGeneratorPlugin] = []
        self._enhancer_plugins: List[MetadataEnhancerPlugin] = []
        self._filter_plugins: List[FileFilterPlugin] = []
        self._lifecycle_plugins: List[LifecyclePlugin] = []
        # 热重载相关
        self._hot_reload_enabled: bool = False
        self._observer = None
        self._plugin_dir: Optional[str] = None
        self._global_config = None
        self._file_hashes: Dict[str, str] = {}  # filepath -> md5 hash

    def register(self, plugin: Plugin, global_config: "Config" = None) -> None:
        """
        注册插件，根据类型自动分类，支持优先级排序

        Args:
            plugin: 插件实例
            global_config: 全局配置对象（可选）
        """
        if plugin.name in self._plugins:
            logger.warning(f"插件 '{plugin.name}' 已存在，将被覆盖")
            self.unregister(plugin.name)

        self._plugins[plugin.name] = plugin

        # 根据类型自动分类，并按优先级排序
        if isinstance(plugin, NFOParserPlugin):
            self._parser_plugins.append(plugin)
            self._parser_plugins.sort(
                key=lambda p: (
                    (
                        -getattr(p, "priority", 50)
                        if not callable(getattr(p, "priority", None))
                        else p.priority
                    ),
                    p.name,
                )
            )
        if isinstance(plugin, VSMETAGeneratorPlugin):
            self._generator_plugins.append(plugin)
            self._generator_plugins.sort(
                key=lambda p: (
                    (
                        -getattr(p, "priority", 50)
                        if not callable(getattr(p, "priority", None))
                        else p.priority
                    ),
                    p.name,
                )
            )
        if isinstance(plugin, MetadataEnhancerPlugin):
            self._enhancer_plugins.append(plugin)
            self._enhancer_plugins.sort(
                key=lambda p: (
                    (
                        -getattr(p, "priority", 50)
                        if not callable(getattr(p, "priority", None))
                        else p.priority
                    ),
                    p.name,
                )
            )
        if isinstance(plugin, FileFilterPlugin):
            self._filter_plugins.append(plugin)
            self._filter_plugins.sort(
                key=lambda p: (
                    (
                        -getattr(p, "priority", 50)
                        if not callable(getattr(p, "priority", None))
                        else p.priority
                    ),
                    p.name,
                )
            )
        if isinstance(plugin, LifecyclePlugin):
            self._lifecycle_plugins.append(plugin)

        # 获取插件优先级用于日志
        try:
            pri = plugin.priority
        except Exception:
            pri = 50

        # 调用注册回调
        try:
            from nfo_to_vsmeta_converter_complete import Config as _Cfg

            reg_cfg = global_config if global_config is not None else _Cfg()
            plugin.on_register(reg_cfg, PluginConfig(plugin_name=plugin.name))
        except Exception as e:
            logger.warning(f"插件 '{plugin.name}' 注册回调异常: {e}")

        logger.info(
            f"插件已注册: {plugin.name} v{plugin.version} (优先级: {pri}) - {plugin.description}"
        )

    def unregister(self, name: str) -> None:
        """
        按名称注销插件

        Args:
            name: 插件名称
        """
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            logger.warning(f"插件 '{name}' 不存在，无法注销")
            return

        # 从各分类列表中移除
        if isinstance(plugin, NFOParserPlugin) and plugin in self._parser_plugins:
            self._parser_plugins.remove(plugin)
        if isinstance(plugin, VSMETAGeneratorPlugin) and plugin in self._generator_plugins:
            self._generator_plugins.remove(plugin)
        if isinstance(plugin, MetadataEnhancerPlugin) and plugin in self._enhancer_plugins:
            self._enhancer_plugins.remove(plugin)
        if isinstance(plugin, FileFilterPlugin) and plugin in self._filter_plugins:
            self._filter_plugins.remove(plugin)
        if isinstance(plugin, LifecyclePlugin) and plugin in self._lifecycle_plugins:
            self._lifecycle_plugins.remove(plugin)

        # 调用注销回调
        try:
            plugin.on_unregister()
        except Exception as e:
            logger.warning(f"插件 '{name}' 注销回调异常: {e}")

        logger.info(f"插件已注销: {name}")

    def load_from_directory(self, plugin_dir: str, global_config: "Config" = None) -> int:
        """
        从目录加载 .py 插件文件，支持依赖管理和拓扑排序

        扫描目录中的 .py 文件，使用 importlib 动态导入，
        查找继承自 Plugin 的类，解析依赖关系后按拓扑排序注册。

        Args:
            plugin_dir: 插件目录路径
            global_config: 全局配置对象（可选）

        Returns:
            成功加载的插件数量
        """
        if not os.path.isdir(plugin_dir):
            logger.warning(f"插件目录不存在: {plugin_dir}")
            return 0

        # 第一阶段：收集所有插件类
        plugin_classes = []

        for filename in sorted(os.listdir(plugin_dir)):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            filepath = os.path.join(plugin_dir, filename)
            module_name = f"_plugin_{os.path.splitext(filename)[0]}"

            try:
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec is None or spec.loader is None:
                    logger.warning(f"无法加载插件文件: {filepath}")
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Plugin)
                        and attr is not Plugin
                        and attr.__module__ == module_name
                    ):
                        plugin_classes.append(attr)

            except Exception as e:
                logger.error(f"加载插件文件 '{filename}' 失败: {e}")

        if not plugin_classes:
            return 0

        # 第二阶段：解析依赖关系
        name_to_class = {}
        for cls in plugin_classes:
            try:
                temp = cls()
                name_to_class[temp.name] = cls
            except Exception as e:
                logger.warning(f"无法实例化插件类 {cls.__name__}: {e}")

        # 构建依赖图
        in_degree = {name: 0 for name in name_to_class}
        graph = {name: [] for name in name_to_class}
        missing_deps = {}

        for name, cls in name_to_class.items():
            try:
                temp = cls()
                for dep in temp.dependencies:
                    if dep in name_to_class:
                        graph[dep].append(name)
                        in_degree[name] += 1
                    else:
                        if name not in missing_deps:
                            missing_deps[name] = []
                        missing_deps[name].append(dep)
                for dep in temp.optional_dependencies:
                    if dep in name_to_class:
                        graph[dep].append(name)
                        in_degree[name] += 1
            except Exception as e:
                logger.warning(f"分析插件 '{name}' 依赖时出错: {e}")

        # 报告缺失的必需依赖
        for name, deps in missing_deps.items():
            logger.error(f"插件 '{name}' 缺少必需依赖: {deps}，已跳过")
            del name_to_class[name]
            if name in in_degree:
                del in_degree[name]
            if name in graph:
                del graph[name]
            # 修正依赖此插件的其他插件的 in_degree
            for n, neighbors in list(graph.items()):
                if name in neighbors:
                    neighbors.remove(name)
                    if n in in_degree:
                        in_degree[n] -= 1

        # 第三阶段：拓扑排序（Kahn算法）
        queue = sorted([name for name, degree in in_degree.items() if degree == 0])
        sorted_names = []

        while queue:
            current = queue.pop(0)
            sorted_names.append(current)
            for neighbor in sorted(graph.get(current, [])):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
                        queue.sort()

        # 检测循环依赖
        if len(sorted_names) != len(name_to_class):
            unresolved = set(name_to_class.keys()) - set(sorted_names)
            logger.error(f"存在循环依赖或依赖解析失败，跳过以下插件: {unresolved}")
            # 只加载已解析的插件

        # 第四阶段：按顺序实例化和注册
        loaded_count = 0
        for name in sorted_names:
            cls = name_to_class[name]
            try:
                plugin_instance = cls()
                self.register(plugin_instance, global_config)
                loaded_count += 1
            except Exception as e:
                logger.error(f"实例化插件 '{name}' 失败: {e}")

        logger.info(f"从目录 '{plugin_dir}' 加载了 {loaded_count} 个插件")
        return loaded_count

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """
        按名称获取插件

        Args:
            name: 插件名称

        Returns:
            插件实例，未找到返回 None
        """
        return self._plugins.get(name)

    def list_plugins(self, sort_by_priority: bool = True) -> List[Dict]:
        """
        列出所有已注册插件的信息

        Args:
            sort_by_priority: 是否按优先级排序，默认 True

        Returns:
            插件信息列表
        """
        result = []
        for p in self._plugins.values():
            info = {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "type": type(p).__name__,
            }
            try:
                info["priority"] = p.priority
            except Exception:
                info["priority"] = 50
            try:
                info["dependencies"] = p.dependencies
            except Exception:
                info["dependencies"] = []
            try:
                info["optional_dependencies"] = p.optional_dependencies
            except Exception:
                info["optional_dependencies"] = []
            try:
                info["config_schema"] = p.config_schema
            except Exception:
                info["config_schema"] = {}
            result.append(info)

        if sort_by_priority:
            result.sort(key=lambda x: (-x["priority"], x["name"]))

        return result

    def get_plugin_config(self, name: str) -> Optional["PluginConfig"]:
        """
        获取指定插件的配置对象

        Args:
            name: 插件名称

        Returns:
            PluginConfig 实例，插件不存在返回 None
        """
        if name not in self._plugins:
            return None
        return PluginConfig(plugin_name=name)

    def update_plugin_config(self, name: str, values: Dict) -> bool:
        """
        更新指定插件的配置

        Args:
            name: 插件名称
            values: 配置键值对

        Returns:
            是否成功
        """
        if name not in self._plugins:
            return False
        config = PluginConfig(plugin_name=name)
        config.update(values)
        # 通知插件配置已更新
        plugin = self._plugins[name]
        try:
            from nfo_to_vsmeta_converter_complete import Config as _Cfg

            global_cfg = self._global_config if self._global_config is not None else _Cfg()
            plugin.on_register(global_cfg, config)
        except Exception as e:
            logger.warning(f"插件 '{name}' 配置更新回调异常: {e}")
        return True

    def run_parser_plugins(self, nfo_path: str, metadata: VideoMetadata) -> VideoMetadata:
        """
        运行所有 NFO 解析插件

        Args:
            nfo_path: NFO 文件路径
            metadata: 当前元数据

        Returns:
            经过所有插件处理后的元数据
        """
        for plugin in self._parser_plugins:
            try:
                result = plugin.parse(nfo_path, metadata)
                if result is not None:
                    metadata = result
            except Exception as e:
                logger.warning(f"NFO 解析插件 '{plugin.name}' 执行异常: {e}")
        return metadata

    def run_generator_plugins(self, metadata: VideoMetadata, vsmeta_data: bytes) -> bytes:
        """
        运行所有 VSMETA 生成插件

        Args:
            metadata: 视频元数据
            vsmeta_data: 当前 VSMETA 二进制数据

        Returns:
            经过所有插件处理后的 VSMETA 数据
        """
        for plugin in self._generator_plugins:
            try:
                vsmeta_data = plugin.generate(metadata, vsmeta_data)
            except Exception as e:
                logger.warning(f"VSMETA 生成插件 '{plugin.name}' 执行异常: {e}")
        return vsmeta_data

    def run_enhancer_plugins(self, metadata: VideoMetadata, filepath: str) -> VideoMetadata:
        """
        运行所有元数据增强插件

        Args:
            metadata: 当前元数据
            filepath: 视频文件路径

        Returns:
            经过所有插件增强后的元数据
        """
        for plugin in self._enhancer_plugins:
            try:
                metadata = plugin.enhance(metadata, filepath)
            except Exception as e:
                logger.warning(f"元数据增强插件 '{plugin.name}' 执行异常: {e}")
        return metadata

    def run_filter_plugins(self, filepath: str, filename: str) -> bool:
        """
        运行所有文件过滤插件

        所有插件都返回 True 时才处理该文件（AND 逻辑）。

        Args:
            filepath: 文件完整路径
            filename: 文件名

        Returns:
            True 表示应该处理该文件
        """
        for plugin in self._filter_plugins:
            try:
                if not plugin.should_process(filepath, filename):
                    return False
            except Exception as e:
                logger.warning(f"文件过滤插件 '{plugin.name}' 执行异常: {e}")
        return True

    def notify_lifecycle(self, event: str, **kwargs) -> None:
        """
        通知生命周期插件

        Args:
            event: 事件名称（on_start/on_file_start/on_file_end/on_finish）
            **kwargs: 传递给回调的参数
        """
        for plugin in self._lifecycle_plugins:
            try:
                handler = getattr(plugin, event, None)
                if handler is not None and callable(handler):
                    handler(**kwargs)
            except Exception as e:
                logger.warning(f"生命周期插件 '{plugin.name}' 事件 '{event}' 异常: {e}")

    # ==================== 热重载功能 ====================

    def enable_hot_reload(self, plugin_dir: str, global_config: "Config" = None) -> bool:
        """
        启用插件热重载

        监控指定目录中的 .py 文件变化，自动重新加载修改过的插件。
        需要 watchdog 库支持。

        Args:
            plugin_dir: 监控的插件目录
            global_config: 全局配置对象

        Returns:
            是否成功启用
        """
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog 库未安装，无法启用热重载。请运行: pip install watchdog")
            return False

        if self._hot_reload_enabled:
            logger.info("热重载已处于启用状态")
            return True

        self._plugin_dir = plugin_dir
        self._global_config = global_config

        # 初始化文件哈希
        self._update_file_hashes()

        # 创建文件系统监控处理器
        class _PluginReloadHandler(FileSystemEventHandler):
            def __init__(self, manager: "PluginManager"):
                self._manager = manager

            def on_modified(self, event):
                if event.is_directory:
                    return
                if event.src_path.endswith(".py") and not os.path.basename(
                    event.src_path
                ).startswith("_"):
                    self._manager._handle_file_change(event.src_path)

            def on_created(self, event):
                if event.is_directory:
                    return
                if event.src_path.endswith(".py") and not os.path.basename(
                    event.src_path
                ).startswith("_"):
                    self._manager._handle_file_change(event.src_path, is_new=True)

            def on_deleted(self, event):
                if event.is_directory:
                    return
                if event.src_path.endswith(".py") and not os.path.basename(
                    event.src_path
                ).startswith("_"):
                    self._manager._handle_file_delete(event.src_path)

        try:
            handler = _PluginReloadHandler(self)
            self._observer = Observer()
            self._observer.schedule(handler, plugin_dir, recursive=False)
            self._observer.daemon = True
            self._observer.start()
            self._hot_reload_enabled = True
            logger.info(f"插件热重载已启用，监控目录: {plugin_dir}")
            return True
        except Exception as e:
            logger.error(f"启用热重载失败: {e}")
            self._observer = None
            return False

    def disable_hot_reload(self) -> None:
        """禁用插件热重载"""
        if not self._hot_reload_enabled:
            return
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception as e:
                logger.warning(f"停止热重载监控时出错: {e}")
            self._observer = None
        self._hot_reload_enabled = False
        logger.info("插件热重载已禁用")

    @property
    def is_hot_reload_enabled(self) -> bool:
        """热重载是否启用"""
        return self._hot_reload_enabled

    def _update_file_hashes(self) -> None:
        """更新所有插件文件的哈希缓存"""
        self._file_hashes = {}
        if not self._plugin_dir or not os.path.isdir(self._plugin_dir):
            return
        for filename in os.listdir(self._plugin_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                filepath = os.path.join(self._plugin_dir, filename)
                try:
                    with open(filepath, "rb") as f:
                        self._file_hashes[filepath] = hashlib.md5(
                            f.read(), usedforsecurity=False
                        ).hexdigest()
                except Exception as e:
                    logger.debug(f"计算文件哈希失败 {filepath}: {e}")

    def _handle_file_change(self, filepath: str, is_new: bool = False) -> None:
        """
        处理插件文件变化事件

        Args:
            filepath: 变化的文件路径
            is_new: 是否为新创建的文件
        """
        # 防抖：检查内容是否真的改变
        try:
            with open(filepath, "rb") as f:
                current_hash = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
        except Exception as e:
            logger.debug(f"读取文件哈希失败 {filepath}: {e}")
            return

        if not is_new and self._file_hashes.get(filepath) == current_hash:
            return  # 内容未变，忽略

        self._file_hashes[filepath] = current_hash
        filename = os.path.basename(filepath)
        module_name = f"_plugin_{os.path.splitext(filename)[0]}"

        logger.info(f"检测到插件文件变化: {filename}，开始重新加载...")

        # 查找并注销旧插件（同一模块的）
        old_names = []
        for name, plugin in list(self._plugins.items()):
            if hasattr(plugin, "__module__") and plugin.__module__ == module_name:
                old_names.append(name)

        # 保存旧配置
        saved_configs = {}
        for name in old_names:
            config = PluginConfig(plugin_name=name)
            saved_configs[name] = config.get_all()
            self.unregister(name)

        # 清除旧模块缓存
        if module_name in sys.modules:
            del sys.modules[module_name]

        # 重新导入模块
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                logger.error(f"无法重新加载插件文件: {filepath}")
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找并注册新插件
            reloaded = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Plugin)
                    and attr is not Plugin
                    and attr.__module__ == module_name
                ):
                    try:
                        plugin_instance = attr()
                        # 恢复保存的配置
                        if plugin_instance.name in saved_configs:
                            pc = PluginConfig(plugin_name=plugin_instance.name)
                            pc.update(saved_configs[plugin_instance.name])
                        self.register(plugin_instance, self._global_config)
                        reloaded.append(plugin_instance.name)
                        logger.info(
                            f"插件热重载成功: {plugin_instance.name} v{plugin_instance.version}"
                        )
                    except Exception as e:
                        logger.error(f"热重载插件 '{attr_name}' 失败: {e}")

            if not reloaded:
                logger.warning(f"文件 {filename} 中未找到有效的插件类")

        except Exception as e:
            logger.error(f"重新加载模块 '{filename}' 失败: {e}")

    def _handle_file_delete(self, filepath: str) -> None:
        """
        处理插件文件删除事件

        Args:
            filepath: 被删除的文件路径
        """
        filename = os.path.basename(filepath)
        module_name = f"_plugin_{os.path.splitext(filename)[0]}"

        removed = []
        for name, plugin in list(self._plugins.items()):
            if hasattr(plugin, "__module__") and plugin.__module__ == module_name:
                self.unregister(name)
                removed.append(name)

        if filepath in self._file_hashes:
            del self._file_hashes[filepath]

        if module_name in sys.modules:
            del sys.modules[module_name]

        if removed:
            logger.info(f"插件文件已删除，已卸载: {removed}")

    def reload_plugin(self, name: str) -> bool:
        """
        手动重载指定插件

        Args:
            name: 插件名称

        Returns:
            是否成功重载
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning(f"插件 '{name}' 不存在，无法重载")
            return False

        if not hasattr(plugin, "__module__") or not plugin.__module__:
            logger.warning(f"插件 '{name}' 无模块信息，无法重载")
            return False

        module_name = plugin.__module__

        # 查找模块对应的文件路径
        module = sys.modules.get(module_name)
        if module is None or not hasattr(module, "__file__") or module.__file__ is None:
            logger.warning(f"无法找到插件 '{name}' 的源文件")
            return False

        filepath = module.__file__
        if not os.path.exists(filepath):
            logger.warning(f"插件 '{name}' 的源文件不存在: {filepath}")
            return False

        self._handle_file_change(filepath)
        return name in self._plugins


# ============================================================================
# 报告生成器
# ============================================================================


class ReportGenerator:
    """
    报告生成器

    支持生成三种格式的转换报告：
    - HTML: 可视化网页报告，带图表和样式
    - CSV: 表格格式，便于导入 Excel
    - TXT: 纯文本格式，便于查看
    """

    def __init__(self, converter):
        """
        初始化报告生成器

        Args:
            converter: 转换器实例（用于获取数据）
        """
        self.converter = converter

    def generate_html(self, details: List[Dict], stats: ConversionStats) -> str:
        """
        生成 HTML 报告

        Args:
            details: 处理详情列表
            stats: 统计信息

        Returns:
            HTML 字符串
        """
        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>NFO to VSMETA 转换报告</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 36px; font-weight: bold; color: #4CAF50; }
        .stat-label { color: #666; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #4CAF50; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:hover { background: #f5f5f5; }
        .success { color: #4CAF50; }
        .error { color: #f44336; }
        .warning { color: #ff9800; }
        .timestamp { color: #999; font-size: 12px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 NFO to VSMETA 转换报告</h1>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{total}</div>
                <div class="stat-label">总文件数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success}</div>
                <div class="stat-label">成功</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{failed}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{skipped}</div>
                <div class="stat-label">跳过</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{duration:.1f}s</div>
                <div class="stat-label">耗时</div>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>文件</th>
                    <th>目录</th>
                    <th>结果</th>
                    <th>详情</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <div class="timestamp">生成时间: {timestamp}</div>
    </div>
</body>
</html>"""

        rows = []
        for detail in details:
            result_class = (
                "success"
                if detail["result"] == "success"
                else "error" if detail["result"] == "error" else "warning"
            )
            rows.append(f"""
                <tr>
                    <td>{html.escape(detail['file'])}</td>
                    <td>{html.escape(detail['dir'])}</td>
                    <td class="{result_class}">{detail['result']}</td>
                    <td>{html.escape(str(detail.get('error', '')))}</td>
                </tr>
            """)

        return html_template.format(
            total=stats.total_files,
            success=stats.success_files,
            failed=stats.failed_files,
            skipped=stats.skipped_files,
            success_rate=stats.success_rate,
            duration=stats.duration,
            rows="\n".join(rows),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def generate_csv(self, details: List[Dict]) -> str:
        """
        生成 CSV 报告

        Args:
            details: 处理详情列表

        Returns:
            CSV 格式字符串
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["文件", "目录", "结果", "错误信息", "处理时间"])

        for detail in details:
            writer.writerow(
                [
                    detail["file"],
                    detail["dir"],
                    detail["result"],
                    detail.get("error", ""),
                    detail.get("time", ""),
                ]
            )

        return output.getvalue()

    def generate_txt(self, details: List[Dict], stats: ConversionStats) -> str:
        """
        生成文本报告

        Args:
            details: 处理详情列表
            stats: 统计信息

        Returns:
            纯文本字符串
        """
        lines = [
            "=" * 60,
            "NFO to VSMETA 转换报告",
            "=" * 60,
            f"总文件数: {stats.total_files}",
            f"成功: {stats.success_files}",
            f"失败: {stats.failed_files}",
            f"跳过: {stats.skipped_files}",
            f"成功率: {stats.success_rate:.1f}%",
            f"耗时: {stats.duration:.1f}秒",
            "-" * 60,
            "",
        ]

        for detail in details:
            lines.append(f"文件: {detail['file']}")
            lines.append(f"目录: {detail['dir']}")
            lines.append(f"结果: {detail['result']}")
            if "error" in detail:
                lines.append(f"错误: {detail['error']}")
            lines.append("-" * 40)

        return "\n".join(lines)


# ============================================================================
# 主转换器
# ============================================================================


class NFOToVSMETAConverter:
    """
    NFO to VSMETA 转换器主类

    整合所有组件，提供完整的转换流程：
    1. 扫描视频文件
    2. 解析 NFO 元数据
    3. 生成 VSMETA 文件
    4. 记录处理状态
    5. 生成报告

    特性：
    - 多线程/多进程并发处理
    - 断点续传
    - 智能重试
    - 进度显示
    - 信号处理（优雅退出）
    """

    def __init__(self, config: Config):
        """
        初始化转换器

        Args:
            config: 配置对象
        """
        self.config = config
        self.nfo_parser = NFOParser(config)
        self.vsmeta_generator = VSMETAGenerator(config)
        self.file_scanner = FileScanner(config)
        self.checkpoint = CheckpointManager(
            config.checkpoint_file, save_interval=getattr(config, "checkpoint_save_interval", 10)
        )
        self.stats = ConversionStats()
        self.report_details: List[Dict] = []
        self.report_generator = ReportGenerator(self)
        self.plugin_manager = PluginManager()  # 插件管理器
        self._interrupted = False
        self._progress_bar = None
        self._stats_lock = threading.Lock()  # 统计信息线程锁

        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

        # 设置日志文件处理器（如果配置了日志文件路径）
        if self.config.log_file:
            file_handler = RotatingFileHandler(
                self.config.log_file,
                maxBytes=self.config.log_file_max_size,
                backupCount=self.config.log_file_backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            logging.getLogger().addHandler(file_handler)

        # Rich 日志处理器（如果可用）
        if HAS_RICH and console:
            rich_handler = RichHandler(console=console, show_time=True, show_path=False)
            rich_handler.setFormatter(logging.Formatter("%(message)s"))
            logging.getLogger().addHandler(rich_handler)

        # 注册信号处理
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """
        设置信号处理器

        处理 SIGINT（Ctrl+C）和 SIGTERM 信号，
        确保中断时保存进度。
        """

        def signal_handler(signum, frame):
            """信号处理函数（仅设置中断标志，不直接执行 IO 或退出）"""
            self._interrupted = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 注册退出时保存
        atexit.register(self.checkpoint.force_save)

    def process_with_checkpoint(self):
        """
        带断点续传的处理流程

        流程：
        1. 扫描目录获取视频文件列表
        2. 过滤已处理的文件
        3. 并发处理待处理文件
        4. 更新统计信息
        5. 显示处理摘要
        """
        logger.info(f"开始扫描目录: {self.config.directory}")

        # === 插件：转换开始生命周期通知 ===
        self.plugin_manager.notify_lifecycle("on_start", config=self.config)

        # === 扫描文件 ===
        files = self.file_scanner.scan()
        self.stats.total_files = len(files)
        logger.info(f"找到 {len(files)} 个视频文件")

        if not files:
            print(f"{Fore.YELLOW}未找到需要处理的视频文件{Style.RESET_ALL}")
            return

        # === 过滤已完成的文件 ===
        pending_files = [
            (d, f) for d, f in files if not self.checkpoint.is_completed(os.path.join(d, f))
        ]

        if len(pending_files) < len(files):
            print(
                f"{Fore.GREEN}跳过 {len(files) - len(pending_files)} 个已处理文件{Style.RESET_ALL}"
            )

        if not pending_files:
            print(f"{Fore.GREEN}所有文件已处理完成！{Style.RESET_ALL}")
            return

        # === 选择执行器 ===
        if self.config.process_mode == "process":
            executor_class = ProcessPoolExecutor
        else:
            executor_class = ThreadPoolExecutor

        # === 创建进度条 ===
        if HAS_RICH and console:
            self._rich_progress = Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            )
            self._rich_task = self._rich_progress.add_task("转换中...", total=len(pending_files))
            self._rich_progress.start()
        elif HAS_TQDM:
            self._progress_bar = tqdm(
                total=len(pending_files),
                desc="转换进度",
                unit="文件",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            )

        # === 并发处理 ===
        completed_count = 0
        with executor_class(max_workers=self.config.max_workers) as executor:
            if self.config.process_mode == "process":
                # 进程模式：使用模块级函数避免序列化问题
                # 将 Config 转换为字典，因为 dataclass 可以通过 asdict 序列化
                config_dict = asdict(self.config)
                args_list = [(d, f, config_dict) for d, f in pending_files]
                results = list(executor.map(_process_file_worker, args_list))

                # 处理结果
                for (directory, filename), result in zip(pending_files, results):
                    # 检查是否被中断
                    if self._interrupted:
                        break

                    self._update_stats(result, directory, filename)
                    completed_count += 1
                    if hasattr(self, "_rich_progress") and self._rich_progress:
                        self._rich_progress.update(self._rich_task, advance=1)
                    elif self._progress_bar:
                        self._progress_bar.update(1)
            else:
                # 线程模式：使用原有逻辑（可以使用绑定方法）
                futures = {
                    executor.submit(self._process_with_retry, d, f): (d, f)
                    for d, f in pending_files
                }

                for future in as_completed(futures):
                    # 检查是否被中断
                    if self._interrupted:
                        break

                    directory, filename = futures[future]
                    try:
                        result = future.result()
                        self._update_stats(result, directory, filename)
                    except Exception as e:
                        logger.error(f"处理失败 {filename}: {e}")
                        self._update_stats({"success": False, "error": str(e)}, directory, filename)

                    completed_count += 1
                    if hasattr(self, "_rich_progress") and self._rich_progress:
                        self._rich_progress.update(self._rich_task, advance=1)
                    elif self._progress_bar:
                        self._progress_bar.update(1)

        # === 清理 ===
        if hasattr(self, "_rich_progress") and self._rich_progress:
            self._rich_progress.stop()
        elif self._progress_bar:
            self._progress_bar.close()
            self._progress_bar = None

        # 中断后强制保存断点
        if self._interrupted:
            print(f"\n{Fore.YELLOW}收到中断信号，正在保存进度...{Style.RESET_ALL}")
            self.checkpoint.force_save()
            print(f"{Fore.GREEN}进度已保存，可以安全退出{Style.RESET_ALL}")

        self.stats.end_time = datetime.now()
        # === 插件：转换结束生命周期通知 ===
        self.plugin_manager.notify_lifecycle("on_finish", stats=self.stats)
        self._print_summary()

    def _process_with_retry(self, directory: str, filename: str) -> Dict:
        """
        带重试的处理

        Args:
            directory: 目录路径
            filename: 文件名

        Returns:
            处理结果字典
        """
        for attempt in range(self.config.retry_attempts):
            try:
                return self._process_single_file(directory, filename)
            except Exception:
                if attempt < self.config.retry_attempts - 1:
                    logger.warning(f"重试 {filename} ({attempt + 1}/{self.config.retry_attempts})")
                    # 指数退避
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise

        return {"success": False, "error": "Max retries exceeded"}

    def _process_single_file(self, directory: str, filename: str) -> Dict:
        """
        处理单个文件

        流程：
        1. 检查 NFO 文件是否存在
        2. 检查是否需要覆盖
        3. 备份已有文件
        4. 解析 NFO
        5. 生成 VSMETA
        6. 写入文件

        Args:
            directory: 目录路径
            filename: 文件名

        Returns:
            处理结果字典
        """
        filepath = os.path.join(directory, filename)

        # === 插件：文件开始处理生命周期通知 ===
        self.plugin_manager.notify_lifecycle("on_file_start", filepath=filepath)

        base_name = os.path.splitext(filename)[0]
        nfo_path = os.path.join(directory, base_name + ".nfo")
        vsmeta_path = filepath + self.config.vsmeta_extension

        # === 预演模式：只返回模拟结果，不实际写入 ===
        if self.config.dry_run:
            if not os.path.exists(nfo_path):
                return {
                    "success": False,
                    "result": "nfo_missing",
                    "error": "[DRY-RUN] NFO 文件不存在",
                }
            if os.path.exists(vsmeta_path):
                return {"success": True, "result": "skipped", "error": "[DRY-RUN] VSMETA 已存在"}
            return {"success": True, "result": "success", "error": "[DRY-RUN] 将会生成 VSMETA"}

        # === 检查 NFO 文件 ===
        if not os.path.exists(nfo_path):
            return {"success": False, "result": "nfo_missing", "error": "NFO 文件不存在"}

        # === 检查是否覆盖 ===
        if os.path.exists(vsmeta_path) and not self.config.overwrite_existing:
            return {"success": True, "result": "skipped", "error": "VSMETA 已存在"}

        # === 备份（先备份再删除，防止数据丢失） ===
        if self.config.enable_backup and os.path.exists(vsmeta_path):
            self._backup_file(vsmeta_path)

        # === 删除已存在的 VSMETA ===
        if os.path.exists(vsmeta_path) and self.config.delete_existing_vsmeta:
            try:
                os.remove(vsmeta_path)
            except Exception as e:
                return {"success": False, "result": "delete_failed", "error": f"删除失败: {e}"}

        # === 解析 NFO ===
        metadata = self.nfo_parser.parse(nfo_path)
        if metadata is None:
            return {"success": False, "result": "parse_error", "error": "NFO 解析失败"}

        # === 插件：NFO 解析后处理 ===
        metadata = self.plugin_manager.run_parser_plugins(nfo_path, metadata)

        # === 插件：元数据增强 ===
        metadata = self.plugin_manager.run_enhancer_plugins(metadata, filepath)

        # === 生成 VSMETA ===
        vsmeta_data = self.vsmeta_generator.generate(metadata)

        # === VSMETA 非空验证 ===
        if len(vsmeta_data) == 0:
            return {
                "success": False,
                "result": "generate_error",
                "error": "VSMETA 生成失败（空数据）",
            }

        # === 插件：VSMETA 生成后处理 ===
        vsmeta_data = self.plugin_manager.run_generator_plugins(metadata, vsmeta_data)

        # === 写入文件 ===
        try:
            with open(vsmeta_path, "wb") as f:
                f.write(vsmeta_data)
        except Exception as e:
            return {"success": False, "result": "write_error", "error": f"写入失败: {e}"}

        # === 生成额外的输出格式（如 NFO） ===
        if "nfo" in self.config.output_formats:
            nfo_output_path = filepath + ".nfo"
            try:
                self._generate_nfo_output(metadata, nfo_output_path)
            except Exception as e:
                logger.warning(f"NFO 输出生成失败 {nfo_output_path}: {e}")

        return {"success": True, "result": "success"}

    def _generate_nfo_output(self, metadata: VideoMetadata, output_path: str):
        """
        生成 Emby/Jellyfin 兼容的 NFO 文件

        Args:
            metadata: 视频元数据对象
            output_path: 输出文件路径
        """
        root = ET.Element("episodedetails")

        # 添加基本字段
        ET.SubElement(root, "title").text = metadata.title or ""
        ET.SubElement(root, "originaltitle").text = metadata.original_title or ""
        ET.SubElement(root, "plot").text = metadata.plot or ""
        ET.SubElement(root, "year").text = str(metadata.year) if metadata.year else ""
        ET.SubElement(root, "rating").text = str(metadata.rating) if metadata.rating else ""
        ET.SubElement(root, "runtime").text = str(metadata.runtime) if metadata.runtime else ""

        # 添加类型
        for genre in metadata.genres:
            ET.SubElement(root, "genre").text = genre

        # 添加导演
        for director in metadata.directors:
            ET.SubElement(root, "director").text = director

        # 添加演员
        for actor in metadata.actors:
            actor_elem = ET.SubElement(root, "actor")
            ET.SubElement(actor_elem, "name").text = actor

        # 添加编剧
        for writer in metadata.writers:
            ET.SubElement(root, "credits").text = writer

        # 添加工作室
        for studio in metadata.studios:
            ET.SubElement(root, "studio").text = studio

        # 添加外部 ID
        if metadata.imdb_id:
            ET.SubElement(root, "imdb").text = metadata.imdb_id
        if metadata.tmdb_id:
            ET.SubElement(root, "tmdbid").text = metadata.tmdb_id

        # 写入文件
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

    def _backup_file(self, filepath: str):
        """
        备份文件

        Args:
            filepath: 文件路径
        """
        try:
            backup_dir = os.path.join(os.path.dirname(filepath), self.config.backup_dir)
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(filepath)
            backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")

            shutil.copy2(filepath, backup_path)

            # 清理过期的备份文件
            self._cleanup_old_backups(os.path.dirname(filepath), filename)
        except Exception as e:
            logger.warning(f"备份失败 {filepath}: {e}")

    def _cleanup_old_backups(self, directory: str, original_filename: str):
        """
        清理过期的备份文件

        Args:
            directory: 文件所在目录
            original_filename: 原始文件名
        """
        backup_dir = os.path.join(directory, self.config.backup_dir)
        if not os.path.exists(backup_dir):
            return

        now = time.time()
        backup_files = []

        # 收集该文件的所有备份
        for filename in os.listdir(backup_dir):
            if filename.startswith(original_filename + "."):
                filepath = os.path.join(backup_dir, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    backup_files.append((filepath, mtime))
                except OSError:
                    continue

        # 按修改时间排序（最新的在前）
        backup_files.sort(key=lambda x: x[1], reverse=True)

        # 清理超过最大数量的备份
        for filepath, _ in backup_files[self.config.backup_max_count :]:
            try:
                os.remove(filepath)
                logger.debug(f"已清理多余备份: {os.path.basename(filepath)}")
            except OSError as e:
                logger.warning(f"清理备份失败: {e}")

        # 清理过期的备份文件
        for filepath, mtime in backup_files:
            file_age = now - mtime
            if file_age > self.config.backup_max_age_days * 86400:
                try:
                    os.remove(filepath)
                    logger.debug(f"已清理过期备份: {os.path.basename(filepath)}")
                except OSError as e:
                    logger.warning(f"清理过期备份失败: {e}")

    def _update_stats(self, result: Dict, directory: str, filename: str):
        """
        更新统计信息（线程安全）

        Args:
            result: 处理结果
            directory: 目录路径
            filename: 文件名
        """
        with self._stats_lock:
            self.stats.processed_files += 1

            detail = {
                "dir": directory,
                "file": filename,
                "result": result.get("result", "error" if not result.get("success") else "success"),
                "error": result.get("error", ""),
                "time": datetime.now().isoformat(),
            }
            self.report_details.append(detail)

            if result.get("success"):
                if result.get("result") == "skipped":
                    self.stats.skipped_files += 1
                else:
                    self.stats.success_files += 1
                    self.checkpoint.mark_completed(os.path.join(directory, filename))
            else:
                self.stats.failed_files += 1
                self.checkpoint.mark_failed(
                    os.path.join(directory, filename), result.get("error", "Unknown error")
                )
                self.stats.errors.append(detail)

            # === 插件：文件处理结束生命周期通知 ===
            self.plugin_manager.notify_lifecycle(
                "on_file_end", filepath=os.path.join(directory, filename), result=result
            )

    def _print_summary(self):
        """打印处理摘要"""
        # Rich 模式
        if HAS_RICH and console:
            table = Table(title="处理结果", box=box.DOUBLE_EDGE, border_style="green")
            table.add_column("指标", style="bold", min_width=15)
            table.add_column("值", justify="right", style="bold")

            table.add_row("总文件数", str(self.stats.total_files))
            table.add_row("✅ 成功", f"[green]{self.stats.success_files}[/green]")
            table.add_row("❌ 失败", f"[red]{self.stats.failed_files}[/red]")
            table.add_row("⏭️ 跳过", f"[yellow]{self.stats.skipped_files}[/yellow]")
            table.add_row("成功率", f"{self.stats.success_rate:.1f}%")
            table.add_row("耗时", f"{self.stats.duration:.1f} 秒")

            console.print(table)

            if self.config.dry_run:
                console.print("[yellow]（预演模式，未实际写入文件）[/yellow]")
            return

        # 非 Rich 模式：使用 colorama 输出
        print(f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}处理完成！{Style.RESET_ALL}")
        if self.config.dry_run:
            print(f"{Fore.YELLOW}（预演模式，未实际写入）{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        print(f"总文件数: {self.stats.total_files}")
        print(f"{Fore.GREEN}成功: {self.stats.success_files}{Style.RESET_ALL}")
        print(f"{Fore.RED}失败: {self.stats.failed_files}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}跳过: {self.stats.skipped_files}{Style.RESET_ALL}")
        print(f"成功率: {self.stats.success_rate:.1f}%")
        print(f"耗时: {self.stats.duration:.1f}秒")

    def _write_report(self, content: str, filename_prefix: str, fmt: str):
        """通用报告写入方法"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext_map = {"html": "html", "csv": "csv", "txt": "txt"}
        ext = ext_map.get(fmt, "txt")
        filename = f"{filename_prefix}_{timestamp}.{ext}"

        # 使用配置的输出目录
        output_dir = self.config.report_output_dir or "."
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{Fore.GREEN}报告已导出: {filepath}{Style.RESET_ALL}")

    def export_report(self, fmt: str = "html"):
        """
        导出处理报告

        Args:
            fmt: 报告格式（html/csv/txt）
        """
        if fmt == "html":
            content = self.report_generator.generate_html(self.report_details, self.stats)
        elif fmt == "csv":
            content = self.report_generator.generate_csv(self.report_details)
        else:
            content = self.report_generator.generate_txt(self.report_details, self.stats)

        self._write_report(content, "conversion_report", fmt)

    def export_performance_report(self, fmt: str = "txt"):
        """导出性能报告（支持 html/csv/txt 格式）"""

        # 构建纯文本内容
        txt_content = f"""性能分析报告
{'=' * 50}
总文件数: {self.stats.total_files}
处理文件数: {self.stats.processed_files}
成功: {self.stats.success_files}
失败: {self.stats.failed_files}
跳过: {self.stats.skipped_files}
成功率: {self.stats.success_rate:.1f}%
总耗时: {self.stats.duration:.1f}秒
平均处理时间: {self.stats.duration / max(self.stats.processed_files, 1):.2f}秒/文件
并发模式: {self.config.process_mode}
工作线程数: {self.config.max_workers}
"""

        if fmt == "html":
            # HTML 格式
            content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>性能分析报告</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:20px auto;}}
table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
th{{background:#f2f2f2;}}</style></head><body>
<h1>性能分析报告</h1>
<table><tr><th>指标</th><th>值</th></tr>
<tr><td>总文件数</td><td>{self.stats.total_files}</td></tr>
<tr><td>处理文件数</td><td>{self.stats.processed_files}</td></tr>
<tr><td>成功</td><td>{self.stats.success_files}</td></tr>
<tr><td>失败</td><td>{self.stats.failed_files}</td></tr>
<tr><td>跳过</td><td>{self.stats.skipped_files}</td></tr>
<tr><td>成功率</td><td>{self.stats.success_rate:.1f}%</td></tr>
<tr><td>总耗时</td><td>{self.stats.duration:.1f}秒</td></tr>
<tr><td>平均处理时间</td><td>{self.stats.duration / max(self.stats.processed_files, 1):.2f}秒/文件</td></tr>
<tr><td>并发模式</td><td>{self.config.process_mode}</td></tr>
<tr><td>工作线程数</td><td>{self.config.max_workers}</td></tr>
</table></body></html>"""
        elif fmt == "csv":
            # CSV 格式
            import io as _io

            buf = _io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["指标", "值"])
            writer.writerow(["总文件数", self.stats.total_files])
            writer.writerow(["处理文件数", self.stats.processed_files])
            writer.writerow(["成功", self.stats.success_files])
            writer.writerow(["失败", self.stats.failed_files])
            writer.writerow(["跳过", self.stats.skipped_files])
            writer.writerow(["成功率", f"{self.stats.success_rate:.1f}%"])
            writer.writerow(["总耗时(秒)", f"{self.stats.duration:.1f}"])
            writer.writerow(
                [
                    "平均处理时间(秒/文件)",
                    f"{self.stats.duration / max(self.stats.processed_files, 1):.2f}",
                ]
            )
            writer.writerow(["并发模式", self.config.process_mode])
            writer.writerow(["工作线程数", self.config.max_workers])
            content = buf.getvalue()
        else:
            # TXT 格式（默认）
            content = txt_content

        self._write_report(content, "performance_report", fmt)

    def export_smart_analysis_report(self, fmt: str = "txt"):
        """导出智能分析报告（支持 html/csv/txt 格式）"""

        # 统计失败原因
        error_types = {}
        for detail in self.report_details:
            if detail["result"] != "success":
                error_types[detail["result"]] = error_types.get(detail["result"], 0) + 1

        # 构建纯文本内容
        txt_lines = [
            "智能分析报告",
            "=" * 50,
            "处理概况:",
            f"- 总文件数: {self.stats.total_files}",
            f"- 成功率: {self.stats.success_rate:.1f}%",
            "",
            "失败原因分布:",
        ]
        for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            txt_lines.append(f"- {error_type}: {count} 个")
        txt_lines.append(f"\n失败文件详情:\n{'-' * 50}")
        for detail in self.report_details:
            if detail["result"] != "success":
                suggestion = self.analyze_error_and_suggest(detail)
                txt_lines.append(f"文件: {detail['file']}")
                txt_lines.append(f"原因: {detail['result']}")
                txt_lines.append(f"建议: {suggestion}")
                txt_lines.append("")

        if fmt == "html":
            # HTML 格式
            error_rows = ""
            for detail in self.report_details:
                if detail["result"] != "success":
                    suggestion = self.analyze_error_and_suggest(detail)
                    error_rows += f"<tr><td>{html.escape(detail['file'])}</td><td>{html.escape(detail['result'])}</td><td>{html.escape(suggestion)}</td></tr>\n"
            error_dist_rows = ""
            for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
                error_dist_rows += f"<tr><td>{html.escape(error_type)}</td><td>{count}</td></tr>\n"
            content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>智能分析报告</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:20px auto;}}
table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
th{{background:#f2f2f2;}}</style></head><body>
<h1>智能分析报告</h1>
<h2>处理概况</h2>
<table><tr><th>指标</th><th>值</th></tr>
<tr><td>总文件数</td><td>{self.stats.total_files}</td></tr>
<tr><td>成功率</td><td>{self.stats.success_rate:.1f}%</td></tr>
</table>
<h2>失败原因分布</h2>
<table><tr><th>原因</th><th>数量</th></tr>{error_dist_rows}</table>
<h2>失败文件详情</h2>
<table><tr><th>文件</th><th>原因</th><th>建议</th></tr>{error_rows}</table>
</body></html>"""
        elif fmt == "csv":
            # CSV 格式
            import io as _io

            buf = _io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["文件", "原因", "建议"])
            for detail in self.report_details:
                if detail["result"] != "success":
                    suggestion = self.analyze_error_and_suggest(detail)
                    writer.writerow([detail["file"], detail["result"], suggestion])
            content = buf.getvalue()
        else:
            # TXT 格式（默认）
            content = "\n".join(txt_lines)

        self._write_report(content, "smart_analysis", fmt)

    def analyze_error_and_suggest(self, detail: Dict) -> str:
        """
        分析错误并给出建议

        Args:
            detail: 错误详情

        Returns:
            修复建议
        """
        result = detail.get("result", "")

        suggestions = {
            "nfo_missing": "请确保视频文件同目录下存在同名 .nfo 文件",
            "parse_error": "NFO 文件格式可能不正确，请检查 XML 语法",
            "write_error": "请检查目录写入权限",
            "delete_failed": "请检查文件权限或手动删除已存在的 VSMETA 文件",
        }

        return suggestions.get(result, "请检查日志获取详细信息")


# ============================================================================
# 交互式配置
# ============================================================================


def _prompt_int(prompt: str, default: int, min_val: int = None, max_val: int = None) -> int:
    """带验证的整数输入"""
    value = input(f"{prompt}（默认 {default}）: ").strip()
    if not value:
        return default
    try:
        result = int(value)
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        return result
    except ValueError:
        return default


def _prompt_float(
    prompt: str, default: float, min_val: float = None, max_val: float = None
) -> float:
    """带验证的浮点数输入"""
    value = input(f"{prompt}（默认 {default}）: ").strip()
    if not value:
        return default
    try:
        result = float(value)
        if min_val is not None:
            result = max(min_val, result)
        if max_val is not None:
            result = min(max_val, result)
        return result
    except ValueError:
        return default


def interactive_config_with_validation() -> Config:
    """
    交互式配置向导

    通过命令行交互方式引导用户配置各项参数。

    Returns:
        配置对象
    """
    print(f"\n{Fore.CYAN}=== 配置向导 ==={Style.RESET_ALL}\n")

    config = Config()

    # 目录设置
    dirs = input("请输入处理目录（多个用逗号分隔，默认当前目录）: ").strip()
    if dirs:
        config.directory = [d.strip() for d in dirs.split(",")]

    # 线程数
    config.max_workers = _prompt_int("线程数", config.max_workers, min_val=1, max_val=16)

    # 图片大小
    config.max_image_size_kb = _prompt_int("图片大小限制 KB", config.max_image_size_kb)

    # 压缩比例
    config.image_compression_ratio = _prompt_float(
        "图片压缩比例 0.1-1.0", config.image_compression_ratio, min_val=0.1, max_val=1.0
    )

    # 重试次数
    config.retry_attempts = _prompt_int("重试次数", config.retry_attempts, min_val=0)

    # 覆盖选项
    overwrite = input("覆盖已存在的 VSMETA 文件？(y/N）: ").strip().lower()
    config.overwrite_existing = overwrite in ("y", "yes")

    # 备份选项
    backup = input("启用备份？(Y/n）: ").strip().lower()
    config.enable_backup = backup not in ("n", "no")

    return config


def recommend_config() -> Config:
    """
    智能推荐配置

    根据 CPU 核心数自动推荐最佳配置。

    Returns:
        推荐的配置对象
    """
    import multiprocessing

    config = Config()

    # 根据 CPU 核心数推荐线程数
    cpu_count = multiprocessing.cpu_count()
    config.max_workers = min(cpu_count, 8)

    # 默认使用线程模式
    config.process_mode = "thread"

    print(f"{Fore.GREEN}推荐配置已生成：")
    print(f"  线程数: {config.max_workers}")
    print(f"  处理模式: {config.process_mode}{Style.RESET_ALL}")

    return config


# ============================================================================
# UI 工具函数
# ============================================================================


def spinner(msg, duration=2):
    """
    显示旋转加载动画

    Args:
        msg: 显示的消息
        duration: 持续时间（秒）
    """
    # Rich 模式
    if HAS_RICH and console:
        with console.status(f"[bold cyan]{msg}[/bold cyan]", spinner="dots"):
            time.sleep(duration)
        return

    # 非 Rich 模式：使用 colorama 动画
    for c in itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]):
        print(f"\r{Fore.LIGHTMAGENTA_EX}{msg} {c}{Style.RESET_ALL}", end="", flush=True)
        time.sleep(0.1)
        duration -= 0.1
        if duration <= 0:
            break
    print("\r", end="")


def show_menu_with_arrows(options, title="NFO to VSMETA 转换器 - 完全优化版"):
    """
    支持上下键选择的菜单

    Args:
        options: 选项列表
        title: 菜单标题

    Returns:
        选中项索引（0 ~ len(options)-1）
        -1: 返回上一级
        len(options): 退出
    """
    # Rich 模式
    if HAS_RICH and console:
        idx = 0
        while True:
            console.clear()

            # 创建菜单表格
            table = Table(
                title=title,
                box=box.DOUBLE_EDGE,
                show_header=False,
                border_style="cyan",
                title_style="bold cyan",
                padding=(0, 2),
            )

            for i, opt in enumerate(options):
                if i == idx:
                    table.add_row(f"[bold green]👉 {i + 1}. {opt}[/bold green]")
                else:
                    table.add_row(f"  [dim]{i + 1}. {opt}[/dim]")

            console.print(table)
            console.print("[dim]↑↓选择 | 回车确定 | b返回 | q退出 | 数字键跳转[/dim]")

            key = readchar.readkey()
            if key in (readchar.key.UP, "w", "W"):
                idx = (idx - 1) % len(options)
            elif key in (readchar.key.DOWN, "s", "S"):
                idx = (idx + 1) % len(options)
            elif key in ("\r", "\n"):
                return idx
            elif key in ("b", "B"):
                return -1
            elif key in ("q", "Q"):
                return len(options)
            elif key.isdigit():
                num = int(key)
                if 1 <= num <= len(options):
                    return num - 1

    # 非 Rich 模式：无 readchar 时的简易回退
    if not HAS_READCHAR:
        print(f"\n{Fore.CYAN}{title}{Style.RESET_ALL}\n")
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")
        choice = input("请输入序号（或直接回车退出）: ").strip()
        if not choice:
            return len(options)
        try:
            num = int(choice)
            if 1 <= num <= len(options):
                return num - 1
        except ValueError:
            pass
        return len(options)

    # 非 Rich 模式：有 readchar 时的交互式菜单
    idx = 0
    while True:
        # 清屏并渲染菜单
        print("\033[2J\033[H")
        print(f"\n{Fore.CYAN}{'🟢' * 8} {Style.BRIGHT}{title}{'🟢' * 8}{Style.RESET_ALL}")
        for i, opt in enumerate(options):
            prefix = "👉" if i == idx else "  "
            color = Fore.GREEN if i == idx else Fore.YELLOW
            print(f"{color}{prefix} {i + 1}. {opt}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'-' * 40}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}↑↓选择，回车确定，b返回，数字/q/exit/回车退出{Style.RESET_ALL}")

        key = readchar.readkey()
        if key in (readchar.key.UP, "w", "W"):
            idx = (idx - 1) % len(options)
        elif key in (readchar.key.DOWN, "s", "S"):
            idx = (idx + 1) % len(options)
        elif key in ("\r", "\n"):
            return idx
        elif key in ("b", "B"):
            return -1
        elif key in ("q", "Q"):
            return len(options)
        elif key.isdigit():
            num = int(key)
            if 1 <= num <= len(options):
                return num - 1


def show_config(config):
    """
    显示当前配置

    Args:
        config: 配置对象
    """
    # Rich 模式
    if HAS_RICH and console:
        table = Table(title="当前配置", box=box.ROUNDED, border_style="cyan", show_lines=True)
        table.add_column("配置项", style="bold yellow", min_width=20)
        table.add_column("值", style="cyan")

        table.add_row("处理目录", str(config.directory))
        table.add_row("文件过滤（通配符）", str(config.file_include_patterns or "全部"))
        table.add_row("文件过滤（正则）", str(config.file_regex or "无"))
        table.add_section()
        table.add_row("图片最大大小", f"{config.max_image_size_kb} KB")
        table.add_row("图片压缩比例", str(config.image_compression_ratio))
        table.add_section()
        table.add_row("线程数", str(config.max_workers))
        table.add_row("重试次数", str(config.retry_attempts))
        table.add_row("重试延迟", f"{config.retry_delay} 秒")
        table.add_row("日志级别", config.log_level)
        table.add_row("处理模式", config.process_mode)
        table.add_section()
        table.add_row("覆盖已有文件", "是" if config.overwrite_existing else "否")
        table.add_row("启用备份", "是" if config.enable_backup else "否")
        table.add_row("预演模式", "是" if config.dry_run else "否")
        table.add_row("输出格式", ", ".join(config.output_formats))
        table.add_row("插件目录", config.plugin_dir)

        console.print(table)
        return

    # 非 Rich 模式：使用 colorama 输出
    print(f"\n{Fore.CYAN}当前配置：{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}目录:{Style.RESET_ALL} {config.directory}")
    print(f"{Fore.YELLOW}文件过滤:{Style.RESET_ALL}")
    print(f"  - 通配符: {config.file_include_patterns or '全部'}")
    print(f"  - 正则: {config.file_regex or '无'}")
    print(f"{Fore.YELLOW}图片设置:{Style.RESET_ALL}")
    print(f"  - 最大大小: {config.max_image_size_kb}KB")
    print(f"  - 压缩比例: {config.image_compression_ratio}")
    print(f"{Fore.YELLOW}处理选项:{Style.RESET_ALL}")
    print(f"  - 线程数: {config.max_workers}")
    print(f"  - 重试次数: {config.retry_attempts}")
    print(f"  - 重试延迟: {config.retry_delay}秒")
    print(f"  - 日志级别: {config.log_level}")
    print(f"  - 处理模式: {config.process_mode}")
    print(f"  - 覆盖已有: {config.overwrite_existing}")
    print(f"  - 启用备份: {config.enable_backup}")
    print()


def parse_semantic_command(cmd, base_config=None):
    """
    解析自然语言/语义化命令

    支持的命令示例:
        - 设置目录 "/path/to/movies" 和 "/path/to/series"
        - 使用8个线程处理，图片大小限制200KB
        - 过滤文件名 "*.mkv" 或正则 ".*1080p.*"
        - 只处理2020年以后的mp4
        - 只处理大于2GB的文件
        - 图片压缩到100KB，压缩比例0.7

    Args:
        cmd: 命令字符串
        base_config: 基础配置（可选）

    Returns:
        解析后的配置对象
    """
    config = copy.deepcopy(base_config) if base_config else Config()
    cmd_lower = cmd.lower()

    # === 目录设置 ===
    if "目录" in cmd or "path" in cmd_lower:
        paths = re.findall(r'"([^"]+)"', cmd)
        if paths:
            config.directory = paths if len(paths) > 1 else paths[0]

    # === 文件格式过滤 ===
    ext_matches = re.findall(r"(mp4|mkv|avi|ts|wmv|rmvb)", cmd_lower)
    if ext_matches:
        config.file_include_patterns = [f"*.{ext}" for ext in ext_matches]

    # === 文件大小过滤 ===
    size_match = re.search(r"大于(\d+)(g|gb|m|mb)", cmd)
    if size_match:
        size_val = int(size_match.group(1))
        unit = size_match.group(2)
        if unit.startswith("g"):
            config.min_size = size_val * 1024 * 1024 * 1024
        else:
            config.min_size = size_val * 1024 * 1024

    # === 年份过滤 ===
    year_match = re.search(r"(\d{4})年以?后", cmd)
    if year_match:
        year = int(year_match.group(1))
        config.file_regex = "|".join(str(y) for y in range(year + 1, year + 10))

    # === 图片大小限制 ===
    img_size_match = re.search(r"(图片|海报|压缩)[^\d]*(\d+)\s*[kK][bB]", cmd)
    if img_size_match:
        config.max_image_size_kb = int(img_size_match.group(2))

    # === 压缩比例 ===
    ratio_match = re.search(r"(压缩比例|压缩比)[^\d]*(0\.\d+|1\.0|1)", cmd)
    if ratio_match:
        config.image_compression_ratio = float(ratio_match.group(2))

    # === 线程数 ===
    thread_match = re.search(r"(线程数|多线程|thread)[^\d]*(\d+)", cmd_lower)
    if thread_match:
        config.max_workers = min(16, max(1, int(thread_match.group(2))))

    # === 重试次数 ===
    retry_match = re.search(r"重试(\d+)次", cmd)
    if retry_match:
        config.retry_attempts = int(retry_match.group(1))

    # === 日志级别 ===
    if "日志" in cmd:
        levels = {"debug": "DEBUG", "info": "INFO", "warning": "WARNING", "error": "ERROR"}
        for k, v in levels.items():
            if k in cmd_lower:
                config.log_level = v
                break

    # === 处理模式 ===
    if "进程" in cmd:
        config.process_mode = "process"
    elif "线程" in cmd:
        config.process_mode = "thread"

    # === 文件过滤（通配符或正则） ===
    if "过滤" in cmd:
        patterns = re.findall(r'"([^"]+)"', cmd)
        if patterns:
            if "*" in patterns[0] or "?" in patterns[0]:
                config.file_include_patterns = patterns
            else:
                config.file_regex = patterns[0]

    # === 关键词过滤（兜底） ===
    keyword_matches = re.findall(r"只处理.*?([\u4e00-\u9fa5a-zA-Z0-9]+)", cmd)
    if keyword_matches and not config.file_regex:
        config.file_regex = "|".join(keyword_matches)

    return config


def create_plugin_template(
    name: str,
    plugin_type: str = "enhancer",
    output_dir: str = "plugins",
    author: str = "Anonymous",
    version: str = "1.0.0",
    description: str = "",
    priority: int = 50,
) -> str:
    """
    创建插件模板文件

    根据指定的插件类型生成完整的插件脚手架，包括：
    - plugin.py: 主插件类
    - __init__.py: 包初始化
    - config.json: 默认配置
    - README.md: 使用说明

    Args:
        name: 插件名称（英文，用于类名和标识）
        plugin_type: 插件类型 (parser|generator|enhancer|filter|lifecycle)
        output_dir: 输出目录
        author: 作者名
        version: 版本号
        description: 插件描述
        priority: 优先级 (0-100)

    Returns:
        生成的插件目录路径
    """
    # 类型映射
    type_mapping = {
        "parser": {
            "base_class": "NFOParserPlugin",
            "method": (
                "\n    def parse(self, nfo_path: str, metadata: 'VideoMetadata') -> 'VideoMetadata':\n"
                '        """\n'
                "        解析/修改 NFO 元数据\n"
                "        \n"
                "        Args:\n"
                "            nfo_path: NFO 文件路径\n"
                "            metadata: 默认解析器已解析的元数据\n"
                "            \n"
                "        Returns:\n"
                "            修改后的元数据，返回 None 表示跳过\n"
                '        """\n'
                "        # TODO: 实现解析逻辑\n"
                "        return metadata\n"
            ),
            "desc": "自定义 NFO 解析插件",
        },
        "generator": {
            "base_class": "VSMETAGeneratorPlugin",
            "method": (
                "\n    def generate(self, metadata: 'VideoMetadata', vsmeta_data: bytes) -> bytes:\n"
                '        """\n'
                "        修改 VSMETA 二进制数据\n"
                "        \n"
                "        Args:\n"
                "            metadata: 视频元数据\n"
                "            vsmeta_data: 默认生成器已生成的 VSMETA 二进制数据\n"
                "            \n"
                "        Returns:\n"
                "            修改后的 VSMETA 二进制数据\n"
                '        """\n'
                "        # TODO: 实现生成逻辑\n"
                "        return vsmeta_data\n"
            ),
            "desc": "自定义 VSMETA 生成插件",
        },
        "enhancer": {
            "base_class": "MetadataEnhancerPlugin",
            "method": (
                "\n    def enhance(self, metadata: 'VideoMetadata', filepath: str) -> 'VideoMetadata':\n"
                '        """\n'
                "        增强元数据\n"
                "        \n"
                "        Args:\n"
                "            metadata: 当前元数据\n"
                "            filepath: 对应的视频文件路径\n"
                "            \n"
                "        Returns:\n"
                "            增强后的元数据\n"
                '        """\n'
                "        # TODO: 实现增强逻辑\n"
                "        return metadata\n"
            ),
            "desc": "元数据增强插件",
        },
        "filter": {
            "base_class": "FileFilterPlugin",
            "method": (
                "\n    def should_process(self, filepath: str, filename: str) -> bool:\n"
                '        """\n'
                "        判断文件是否应该被处理\n"
                "        \n"
                "        Args:\n"
                "            filepath: 文件完整路径\n"
                "            filename: 文件名\n"
                "            \n"
                "        Returns:\n"
                "            True 表示应该处理，False 表示跳过\n"
                '        """\n'
                "        # TODO: 实现过滤逻辑\n"
                "        return True\n"
            ),
            "desc": "文件过滤插件",
        },
        "lifecycle": {
            "base_class": "LifecyclePlugin",
            "method": (
                "\n    def on_start(self, config) -> None:\n"
                '        """转换开始时回调"""\n'
                "        pass\n"
                "\n"
                "    def on_file_start(self, filepath: str) -> None:\n"
                '        """单个文件开始处理时回调"""\n'
                "        pass\n"
                "\n"
                "    def on_file_end(self, filepath: str, result: dict) -> None:\n"
                '        """单个文件处理结束时回调"""\n'
                "        pass\n"
                "\n"
                "    def on_finish(self, stats) -> None:\n"
                '        """转换全部完成时回调"""\n'
                "        pass\n"
            ),
            "desc": "生命周期钩子插件",
        },
    }

    if plugin_type not in type_mapping:
        available = ", ".join(type_mapping.keys())
        raise ValueError(f"未知的插件类型: '{plugin_type}'，可选类型: {available}")

    type_info = type_mapping[plugin_type]
    class_name = "".join(word.capitalize() for word in name.split("_"))
    plugin_id = name.lower().replace(" ", "_")
    desc = description or f"{name} - {type_info['desc']}"

    # 确保输出目录存在
    plugin_dir = os.path.join(output_dir, plugin_id)
    os.makedirs(plugin_dir, exist_ok=True)

    # 生成 plugin.py
    plugin_code = f'''"""
{desc}

作者: {author}
版本: {version}
类型: {plugin_type}
"""

from nfo_to_vsmeta_converter_complete import (
    {type_info["base_class"]},
    VideoMetadata,
    Config,
    PluginConfig,
)


class {class_name}({type_info["base_class"]}):
    """
    {desc}
    """
    
    @property
    def name(self) -> str:
        """插件唯一标识名称"""
        return "{plugin_id}"
    
    @property
    def version(self) -> str:
        """插件版本号"""
        return "{version}"
    
    @property
    def description(self) -> str:
        """插件功能描述"""
        return "{desc}"
    
    @property
    def priority(self) -> int:
        """插件优先级 (0-100)，数字越大越先执行"""
        return {priority}
    
    @property
    def dependencies(self) -> list:
        """必需依赖的插件名称列表"""
        return []
    
    @property
    def optional_dependencies(self) -> list:
        """可选依赖的插件名称列表"""
        return []
    
    @property
    def config_schema(self) -> dict:
        """
        配置项定义，用于 WebUI 自动生成配置表单
        格式: {{"key": {{"type": "string", "default": "", "description": "..."}}}}
        """
        return {{}}
    
    def on_register(self, config: Config, plugin_config: PluginConfig = None) -> None:
        """
        注册时回调
        
        Args:
            config: 全局配置对象
            plugin_config: 插件专属配置对象
        """
        # TODO: 初始化插件，读取配置
        # 示例: self.api_key = plugin_config.get("api_key") if plugin_config else ""
        pass
    
    def on_unregister(self) -> None:
        """注销时回调，用于清理资源"""
        pass
{type_info["method"]}
'''

    plugin_file = os.path.join(plugin_dir, "plugin.py")
    with open(plugin_file, "w", encoding="utf-8") as f:
        f.write(plugin_code)

    # 生成 __init__.py
    init_file = os.path.join(plugin_dir, "__init__.py")
    with open(init_file, "w", encoding="utf-8") as f:
        f.write(f"from .plugin import {class_name}\n\n__all__ = ['{class_name}']\n")

    # 生成 config.json
    config_file = os.path.join(plugin_dir, "config.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2, ensure_ascii=False)

    # 生成 README.md
    readme_file = os.path.join(plugin_dir, "README.md")
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n{desc}\n\n")
        f.write(f"- **作者**: {author}\n")
        f.write(f"- **版本**: {version}\n")
        f.write(f"- **类型**: {plugin_type}\n")
        f.write(f"- **优先级**: {priority}\n\n")
        f.write("## 安装\n\n")
        f.write("将此目录复制到转换器的 `plugins/` 目录下，重启转换器或使用热重载功能。\n\n")
        f.write("## 配置\n\n")
        f.write("编辑 `config.json` 或在 WebUI 插件管理页面中配置。\n\n")
        f.write("## 开发\n\n")
        f.write("修改 `plugin.py` 后，如果启用了热重载，插件会自动重新加载。\n")

    logger.info(f"插件模板已创建: {plugin_dir}")
    return plugin_dir


# ============================================================================
# 主函数
# ============================================================================


def main():
    """
    主函数

    程序入口，支持三种运行模式：
    1. 命令行模式：直接指定参数运行
    2. 交互模式：通过问答配置参数
    3. 菜单模式：通过上下键菜单选择操作
    """
    # === 命令行参数解析 ===
    parser = argparse.ArgumentParser(description="NFO to VSMETA 转换器 - 完全优化版")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径")
    parser.add_argument("-d", "--directory", help="处理目录")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的文件")
    parser.add_argument("--delete-existing", action="store_true", help="删除已存在的VSMETA文件")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别",
    )
    parser.add_argument("--log-file", help="日志文件路径，启用后将日志写入文件")
    parser.add_argument("--workers", type=int, help="线程数")
    parser.add_argument("--no-backup", action="store_true", help="禁用备份")
    parser.add_argument("--dry-run", action="store_true", help="预演模式，不实际写入文件")
    parser.add_argument("--plugin-dir", help="插件目录路径")
    parser.add_argument("--load-plugins", action="store_true", help="自动加载插件")
    parser.add_argument("--create-plugin", metavar="NAME", help="创建插件模板脚手架")
    parser.add_argument(
        "--plugin-type",
        choices=["parser", "generator", "enhancer", "filter", "lifecycle"],
        default="enhancer",
        help="插件类型 (默认: enhancer)",
    )
    parser.add_argument(
        "--plugin-output-dir", default="plugins", help="插件输出目录 (默认: plugins)"
    )
    parser.add_argument("--plugin-author", default="Anonymous", help="插件作者")
    parser.add_argument("--plugin-version", default="1.0.0", help="插件版本 (默认: 1.0.0)")
    parser.add_argument("--plugin-description", default="", help="插件描述")
    parser.add_argument(
        "--plugin-priority", type=int, default=50, help="插件优先级 0-100 (默认: 50)"
    )
    parser.add_argument("--version", action="version", version="NFO to VSMETA 转换器 v2.0.1")
    parser.add_argument("--no-color", action="store_true", help="强制禁用 ANSI 颜色输出")
    parser.add_argument("--report-dir", help="报告输出目录，默认为当前目录")
    parser.add_argument(
        "--output-formats", help="输出格式列表（逗号分隔），支持 vsmeta 和 nfo，默认为 vsmeta"
    )
    args = parser.parse_args()

    # === 处理 --create-plugin 参数 ===
    if args.create_plugin:
        try:
            path = create_plugin_template(
                name=args.create_plugin,
                plugin_type=args.plugin_type,
                output_dir=args.plugin_output_dir,
                author=args.plugin_author,
                version=args.plugin_version,
                description=args.plugin_description,
                priority=args.plugin_priority,
            )
            print(f"\n{'=' * 50}")
            print("✅ 插件模板创建成功!")
            print(f"📁 路径: {path}")
            print(f"📝 类型: {args.plugin_type}")
            print("=" * 50 + "\n")
        except Exception as e:
            print(f"\n❌ 创建插件模板失败: {e}\n")
            sys.exit(1)
        return

    # === 处理 --no-color 参数 ===
    if args.no_color:
        global USE_COLOR, Fore, Style
        USE_COLOR = False

        class _NoColorFore:
            """无颜色输出的 Fore 替代类"""

            CYAN = GREEN = YELLOW = RED = LIGHTMAGENTA_EX = ""
            LIGHTBLACK_EX = LIGHTYELLOW_EX = LIGHTCYAN_EX = LIGHTGREEN_EX = ""
            BRIGHT = ""

        class _NoColorStyle:
            """无颜色输出的 Style 替代类"""

            RESET_ALL = BRIGHT = ""

        Fore = _NoColorFore()
        Style = _NoColorStyle()

    # === 命令行模式 ===
    if args.directory or args.overwrite or args.delete_existing or args.workers or args.no_backup:
        config = Config.from_file(args.config)
        if args.directory:
            config.directory = [args.directory]
        if args.overwrite:
            config.overwrite_existing = True
        if args.delete_existing:
            config.delete_existing_vsmeta = True
        if args.workers:
            config.max_workers = args.workers
        if args.no_backup:
            config.enable_backup = False
        if args.dry_run:
            config.dry_run = True
        if args.plugin_dir:
            config.plugin_dir = args.plugin_dir
        if args.load_plugins:
            config.auto_load_plugins = True
        if args.report_dir:
            config.report_output_dir = args.report_dir
        if args.output_formats:
            config.output_formats = [fmt.strip().lower() for fmt in args.output_formats.split(",")]
        config.log_level = args.log_level
        if args.log_file:
            config.log_file = args.log_file

        converter = NFOToVSMETAConverter(config)
        # 自动加载插件
        if config.auto_load_plugins:
            converter.plugin_manager.load_from_directory(config.plugin_dir)
        converter.process_with_checkpoint()
        return

    # === 交互模式 ===
    if args.interactive:
        config = interactive_config_with_validation()
        converter = NFOToVSMETAConverter(config)
        converter.process_with_checkpoint()
        return

    # === 菜单模式 ===
    config = Config.from_file(args.config)
    menu_options = [
        "⭐ 使用默认配置运行",
        "🔧 交互式配置并运行",
        "📂 从配置文件加载并运行",
        "💾 保存当前配置到文件",
        "📄 显示当前配置",
        "🗑️ 清除断点文件",
        "📄 导出处理报告",
        "📊 导出性能分析报告",
        "📈 导出智能分析报告",
        "🛠️ 智能重试失败文件",
        "🔌 插件管理（查看/加载/卸载）",
        "🤖 智能助手/语义命令",
        "❌ 退出 (q/exit/回车)",
    ]
    converter = None

    while True:
        idx = show_menu_with_arrows(menu_options)

        # 退出
        if idx == len(menu_options) or idx == -1:
            print(f"{Fore.GREEN}再见！{Style.RESET_ALL}")
            break

        elif idx == 0:
            # 使用默认配置运行
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()

        elif idx == 1:
            # 交互式配置并运行
            config = interactive_config_with_validation()
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()

        elif idx == 2:
            # 从配置文件加载并运行
            config_path = input(
                f"{Fore.CYAN}>> {Style.RESET_ALL}请输入配置文件路径 (默认: config.json): "
            ).strip()
            if not config_path:
                config_path = "config.json"
            config = Config.from_file(config_path)
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()

        elif idx == 3:
            # 保存当前配置到文件
            config_path = input(
                f"{Fore.CYAN}>> {Style.RESET_ALL}请输入保存路径 (默认: config.json): "
            ).strip()
            if not config_path:
                config_path = "config.json"
            config.save_to_file(config_path)
            print(f"{Fore.GREEN}配置已保存到 {config_path}{Style.RESET_ALL}")

        elif idx == 4:
            # 显示当前配置
            show_config(config)

        elif idx == 5:
            # 清除断点文件
            confirm = (
                input(f"{Fore.YELLOW}确定要清除断点文件吗？(y/N): {Style.RESET_ALL}")
                .strip()
                .lower()
            )
            if confirm not in ("y", "yes"):
                print("已取消")
                continue
            try:
                os.remove(config.checkpoint_file)
                print(f"{Fore.GREEN}断点文件已清除{Style.RESET_ALL}")
            except FileNotFoundError:
                print(f"{Fore.YELLOW}断点文件不存在{Style.RESET_ALL}")

        elif idx == 6:
            # 导出处理报告
            if converter is None:
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                converter.export_report("txt")
                converter.export_report("csv")
                converter.export_report("html")

        elif idx == 7:
            # 导出性能分析报告
            if converter is None:
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                converter.export_performance_report("txt")
                converter.export_performance_report("csv")

        elif idx == 8:
            # 导出智能分析报告
            if converter is None:
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                converter.export_smart_analysis_report("txt")
                converter.export_smart_analysis_report("csv")
                converter.export_smart_analysis_report("html")

        elif idx == 9:
            # 智能重试失败文件
            if converter is None or not hasattr(converter, "report_details"):
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                fail_details = [
                    d
                    for d in converter.report_details
                    if d["result"] in ("error", "nfo_missing", "delete_failed")
                ]
                if not fail_details:
                    print(f"{Fore.GREEN}没有可重试的失败文件！{Style.RESET_ALL}")
                    input("\n按回车键继续...")
                    continue

                # 统计失败原因
                reason_count = {}
                for d in fail_details:
                    reason = d["result"]
                    reason_count[reason] = reason_count.get(reason, 0) + 1

                print(f"{Fore.LIGHTYELLOW_EX}失败原因分布：{Style.RESET_ALL}")
                for k, v in reason_count.items():
                    print(f"  {k}: {v} 个")
                print()

                print("失败文件及修复建议：")
                for i, d in enumerate(fail_details, 1):
                    suggest = converter.analyze_error_and_suggest(d)
                    print(
                        f"{i}. {d['file']} | {d['result']} | {d.get('error', '')} | 建议: {suggest}"
                    )

                print("\n1. 全部重试")
                print("2. 仅重试NFO缺失")
                print("3. 仅重试转换错误")
                print("4. 仅重试删除失败")
                print("5. 自动修复可修复问题后重试")
                opt = input("请选择重试类型（回车默认全部）: ").strip()

                if opt == "2":
                    retry_list = [d for d in fail_details if d["result"] == "nfo_missing"]
                elif opt == "3":
                    retry_list = [d for d in fail_details if d["result"] == "error"]
                elif opt == "4":
                    retry_list = [d for d in fail_details if d["result"] == "delete_failed"]
                elif opt == "5":
                    retry_list = []
                    for d in fail_details:
                        if d["result"] == "nfo_missing" or (
                            d["result"] == "error"
                            and "补全" in converter.analyze_error_and_suggest(d)
                        ):
                            retry_list.append(d)
                    print(
                        f"{Fore.LIGHTCYAN_EX}即将自动修复并重试 {len(retry_list)} 个文件...{Style.RESET_ALL}"
                    )
                else:
                    retry_list = fail_details

                # 重试前确认
                print(f"{Fore.LIGHTCYAN_EX}即将重试 {len(retry_list)} 个文件...{Style.RESET_ALL}")
                confirm = (
                    input(f"{Fore.YELLOW}确定要重试这些文件吗？(y/N): {Style.RESET_ALL}")
                    .strip()
                    .lower()
                )
                if confirm not in ("y", "yes"):
                    print("已取消")
                    continue

                success, fail = 0, 0
                for d in retry_list:
                    try:
                        converter._process_with_retry(d["dir"], d["file"])
                        success += 1
                    except Exception:
                        fail += 1
                print(f"{Fore.GREEN}重试完成，成功: {success}，失败: {fail}{Style.RESET_ALL}")

        elif idx == 10:
            # 插件管理（查看/加载/卸载）
            if converter is None:
                converter = NFOToVSMETAConverter(config)
            pm = converter.plugin_manager

            while True:
                print(f"\n{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}插件管理{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")

                # 显示已注册插件列表
                plugins = pm.list_plugins()
                if plugins:
                    print(f"\n{Fore.GREEN}已注册插件 ({len(plugins)} 个):{Style.RESET_ALL}")
                    for i, p in enumerate(plugins, 1):
                        print(
                            f"  {i}. {p['name']} v{p['version']} [{p['type']}] - {p['description']}"
                        )
                else:
                    print(f"\n{Fore.YELLOW}当前没有已注册的插件{Style.RESET_ALL}")

                print("\n操作选项:")
                print("  1. 从目录加载插件")
                print("  2. 列出所有插件")
                print("  3. 卸载插件")
                print("  0. 返回主菜单")

                choice = input(f"\n{Fore.CYAN}>> {Style.RESET_ALL}请选择操作: ").strip()

                if choice == "0":
                    break
                elif choice == "1":
                    # 从目录加载插件
                    dir_path = input(
                        f"{Fore.CYAN}>> {Style.RESET_ALL}请输入插件目录路径 (默认: {config.plugin_dir}): "
                    ).strip()
                    if not dir_path:
                        dir_path = config.plugin_dir
                    count = pm.load_from_directory(dir_path)
                    print(f"{Fore.GREEN}成功加载 {count} 个插件{Style.RESET_ALL}")
                elif choice == "2":
                    # 列出所有插件
                    plugins = pm.list_plugins()
                    if plugins:
                        print(f"\n{Fore.GREEN}已注册插件 ({len(plugins)} 个):{Style.RESET_ALL}")
                        for i, p in enumerate(plugins, 1):
                            print(
                                f"  {i}. {p['name']} v{p['version']} [{p['type']}] - {p['description']}"
                            )
                    else:
                        print(f"{Fore.YELLOW}当前没有已注册的插件{Style.RESET_ALL}")
                elif choice == "3":
                    # 卸载插件
                    plugins = pm.list_plugins()
                    if not plugins:
                        print(f"{Fore.YELLOW}当前没有已注册的插件{Style.RESET_ALL}")
                    else:
                        name = input(
                            f"{Fore.CYAN}>> {Style.RESET_ALL}请输入要卸载的插件名称: "
                        ).strip()
                        if name:
                            pm.unregister(name)
                            print(f"{Fore.GREEN}插件 '{name}' 已卸载{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.YELLOW}未输入插件名称{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}无效选项{Style.RESET_ALL}")

                input("\n按回车键继续...")

        elif idx == 11:
            # 智能助手/语义命令
            print(
                f"{Fore.LIGHTCYAN_EX}请输入你的需求（如：只处理2020年以后的mp4，线程数8，图片压缩到100KB等）：{Style.RESET_ALL}"
            )
            cmd = input(f"{Fore.CYAN}>> {Style.RESET_ALL}").strip()
            if not cmd:
                print(f"{Fore.YELLOW}未输入任何内容，已返回菜单。{Style.RESET_ALL}")
                input("\n按回车键继续...")
                continue

            rec = parse_semantic_command(cmd, config)
            print(f"\n{Fore.LIGHTGREEN_EX}解析结果推荐配置如下：{Style.RESET_ALL}")
            for field in rec.__dict__:
                print(
                    f"{Fore.LIGHTYELLOW_EX}{field}{Style.RESET_ALL}: {Fore.CYAN}{getattr(rec, field)}{Style.RESET_ALL}"
                )

            accept = (
                input(f"\n{Fore.GREEN}是否采纳推荐配置？(Y/n): {Style.RESET_ALL}").strip().lower()
            )
            if accept in ("", "y", "yes"):
                config = rec
                print(f"{Fore.GREEN}已采纳智能助手推荐配置！{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}未采纳，配置未变更。{Style.RESET_ALL}")

        input("\n按回车键继续...")


if __name__ == "__main__":
    main()
