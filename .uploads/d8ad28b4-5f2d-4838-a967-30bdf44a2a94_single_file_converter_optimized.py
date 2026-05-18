#!/usr/bin/env python
"""
NFO to VSMETA Converter - 完全优化版
包含所有优化功能：多线程、进度条、断点续传、智能重试、配置验证等
"""
import os
import xml.dom.minidom as xmldom
import base64
import hashlib
import time
import io
import logging
import json
import argparse
import pickle
import shutil
import concurrent.futures
import threading
from typing import List, Tuple, Optional, Dict, Union, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from functools import wraps
import sys
import fnmatch
import re
import csv
import multiprocessing
import statistics
import glob
import itertools

# 可选依赖：Pillow
try:
    from PIL import Image  # type: ignore
    HAS_PIL = True
except ImportError:  # 优雅降级
    HAS_PIL = False

# 可选依赖：colorama
try:
    from colorama import init, Fore, Style  # type: ignore
    init(autoreset=True)
except ImportError:
    class _ColorFallback:
        def __getattr__(self, name):
            return ''
    def init(*_args, **_kwargs):  # type: ignore
        return None
    Fore = Style = _ColorFallback()  # type: ignore

# 可选依赖：readchar（仅用于交互菜单）
try:
    import readchar  # type: ignore
    HAS_READCHAR = True
except ImportError:
    HAS_READCHAR = False

# 尝试导入tqdm，如果没有则使用简单进度显示
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("提示: 安装 tqdm 可获得更好的进度显示: pip install tqdm")

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """配置类"""
    directory: Union[str, List[str]] = r'/volume1/video/Links/Movie/'
    poster_suffix: str = '-poster.jpg'
    fanart_suffix: str = '-fanart.jpg'
    supported_video_formats: Tuple[str, ...] = ('.mkv', '.mp4', '.rmvb', '.avi', '.wmv', '.ts')
    ignored_extensions: Tuple[str, ...] = ('.vsmeta', '.jpg', '.nfo', '.srt', '.ass', '.ssa', '.png', '.db')
    max_image_size_kb: int = 200
    image_compression_ratio: float = 0.8
    base64_line_length: int = 76
    log_level: str = 'INFO'
    overwrite_existing: bool = False
    delete_existing_vsmeta: bool = False
    max_workers: int = 4  # 多线程工作数
    enable_backup: bool = True  # 是否启用备份
    retry_attempts: int = 3  # 重试次数
    retry_delay: float = 2.0  # 重试延迟
    file_include_patterns: Optional[List[str]] = None  # 通配符过滤
    file_regex: Optional[str] = None  # 正则过滤
    process_mode: str = 'thread'  # 'thread' or 'process'
    progress_style: str = 'default'  # 'default', 'rocket', 'rainbow', etc.
    min_size: Optional[int] = None  # 新增，单位字节，None为不限

    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """从配置文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 兼容单目录和多目录
            directory = data.get('directory', cls.directory)
            if isinstance(directory, str):
                if any(sep in directory for sep in [',', ';', ' '] ):
                    directory = [d.strip() for d in re.split(r'[;,\s]+', directory) if d.strip()]
                else:
                    directory = [directory]
            return cls(
                directory=directory,
                poster_suffix=data.get('poster_suffix', cls.poster_suffix),
                fanart_suffix=data.get('fanart_suffix', cls.fanart_suffix),
                supported_video_formats=tuple(data.get('supported_video_formats', list(cls.supported_video_formats))),
                ignored_extensions=tuple(data.get('ignored_extensions', list(cls.ignored_extensions))),
                max_image_size_kb=data.get('max_image_size_kb', cls.max_image_size_kb),
                image_compression_ratio=data.get('image_compression_ratio', cls.image_compression_ratio),
                base64_line_length=data.get('base64_line_length', cls.base64_line_length),
                log_level=data.get('log_level', cls.log_level),
                overwrite_existing=data.get('overwrite_existing', cls.overwrite_existing),
                delete_existing_vsmeta=data.get('delete_existing_vsmeta', cls.delete_existing_vsmeta),
                max_workers=data.get('max_workers', cls.max_workers),
                enable_backup=data.get('enable_backup', cls.enable_backup),
                retry_attempts=data.get('retry_attempts', cls.retry_attempts),
                retry_delay=data.get('retry_delay', cls.retry_delay),
                file_include_patterns=data.get('file_include_patterns'),
                file_regex=data.get('file_regex'),
                process_mode=data.get('process_mode', cls.process_mode),
                progress_style=data.get('progress_style', cls.progress_style),
                min_size=data.get('min_size')
            )
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
            return cls()

    def save_to_file(self, config_path: str) -> None:
        """保存配置到文件"""
        data = self.__dict__.copy()
        # 兼容保存单目录
        if isinstance(data['directory'], list) and len(data['directory']) == 1:
            data['directory'] = data['directory'][0]
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

@dataclass
class ConversionStats:
    """转换统计信息"""
    total_files: int = 0
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_size_mb: float = 0.0
    processed_files: Set[str] = field(default_factory=set)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.success_count / self.total_files * 100) if self.total_files > 0 else 0
    
    @property
    def duration(self) -> float:
        """处理时长"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0
    
    @property
    def processing_speed(self) -> float:
        """处理速度"""
        return self.total_files / self.duration if self.duration > 0 else 0

class ConfigValidator:
    """配置验证器"""
    @staticmethod
    def validate_config(config: Config) -> List[str]:
        """验证配置有效性"""
        errors = []
        # 检查目录是否存在（支持多目录）
        dirs = config.directory if isinstance(config.directory, list) else [config.directory]
        for d in dirs:
            if not Path(d).exists():
                errors.append(f"目录不存在: {d}")
        # 检查图片大小设置
        if config.max_image_size_kb < 10:
            errors.append("图片大小不能小于10KB")
        elif config.max_image_size_kb > 1000:
            errors.append("图片大小不能大于1000KB")
        # 检查压缩比例
        if not 0.1 <= config.image_compression_ratio <= 1.0:
            errors.append("压缩比例必须在0.1到1.0之间")
        # 检查线程数
        if config.max_workers < 1:
            errors.append("线程数不能小于1")
        elif config.max_workers > 16:
            errors.append("线程数不能大于16")
        # 检查重试参数
        if config.retry_attempts < 0:
            errors.append("重试次数不能为负数")
        if config.retry_delay < 0:
            errors.append("重试延迟不能为负数")
        return errors

def retry_on_error(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"第 {attempt + 1} 次尝试失败: {e}，{delay}秒后重试")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class InteractiveConfig:
    """交互式配置类（进一步美化）"""
    @staticmethod
    def get_user_input(prompt: str, default: Optional[str] = '', required: bool = True, help_text: Optional[str] = None) -> str:
        while True:
            try:
                prefix = f"{Fore.CYAN}👉 {Style.RESET_ALL}"
                dft = default or ''
                if dft:
                    full_prompt = f"{Fore.YELLOW}*{prompt}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(默认: {dft}, '.'跳过, '?'帮助){Style.RESET_ALL}"
                else:
                    full_prompt = f"{Fore.YELLOW}*{prompt}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}('.'跳过, '?'帮助){Style.RESET_ALL}"
                user_input = input(prefix + full_prompt)
                if user_input == '?':
                    print(Fore.GREEN + (help_text or "无详细帮助。"))
                    continue
                if user_input == '.':
                    return dft
                if user_input == '':
                    return dft
                if not required or user_input:
                    return user_input
                print(Fore.RED + "此字段为必填项，请输入有效值。")
            except (KeyboardInterrupt, EOFError):
                print(Fore.YELLOW + "\n用户中断输入，已退出。")
                sys.exit(0)

    @staticmethod
    def get_yes_no(prompt: str, default: Optional[bool] = True, help_text: Optional[str] = None) -> bool:
        while True:
            try:
                prefix = f"{Fore.CYAN}👉 {Style.RESET_ALL}"
                dft = default if default is not None else True
                default_str = "Y" if dft else "N"
                full_prompt = f"{Fore.YELLOW}*{prompt}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(Y/N, 默认: {default_str}, '.'跳过, '?'帮助){Style.RESET_ALL}"
                user_input = input(prefix + full_prompt)
                user_input = user_input.strip().upper()
                if user_input == '?':
                    print(Fore.GREEN + (help_text or "请输入 Y 或 N，回车为默认，'.'跳过。"))
                    continue
                if user_input == '.':
                    return dft
                if user_input == '':
                    return dft
                elif user_input in ['Y', 'YES']:
                    return True
                elif user_input in ['N', 'NO']:
                    return False
                else:
                    print(Fore.RED + "请输入 Y 或 N")
            except (KeyboardInterrupt, EOFError):
                print(Fore.YELLOW + "\n用户中断输入，已退出。")
                sys.exit(0)

    @staticmethod
    def get_number(prompt: str, default: Optional[int], min_val: int = 0, max_val: Optional[int] = None, help_text: Optional[str] = None) -> int:
        while True:
            try:
                prefix = f"{Fore.CYAN}👉 {Style.RESET_ALL}"
                dft = default if default is not None else 0
                full_prompt = f"{Fore.YELLOW}*{prompt}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(默认: {dft}, '.'跳过, '?'帮助){Style.RESET_ALL}"
                user_input = input(prefix + full_prompt)
                if user_input == '?':
                    print(Fore.GREEN + (help_text or f"请输入{min_val}到{max_val if max_val is not None else '无限'}之间的整数。"))
                    continue
                if user_input == '.':
                    return dft
                if user_input == '':
                    return dft
                value = int(user_input)
                if value < min_val:
                    print(Fore.RED + f"数值不能小于 {min_val}")
                    continue
                if max_val is not None and value > max_val:
                    print(Fore.RED + f"数值不能大于 {max_val}")
                    continue
                return value
            except ValueError:
                print(Fore.RED + "请输入有效的数字")
            except (KeyboardInterrupt, EOFError):
                print(Fore.YELLOW + "\n用户中断输入，已退出。")
                sys.exit(0)

    @staticmethod
    def get_float(prompt: str, default: Optional[float], min_val: float = 0.0, max_val: float = 1.0, help_text: Optional[str] = None) -> float:
        while True:
            try:
                prefix = f"{Fore.CYAN}👉 {Style.RESET_ALL}"
                dft = default if default is not None else 0.0
                full_prompt = f"{Fore.YELLOW}*{prompt}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(默认: {dft}, '.'跳过, '?'帮助){Style.RESET_ALL}"
                user_input = input(prefix + full_prompt)
                if user_input == '?':
                    print(Fore.GREEN + (help_text or f"请输入{min_val}到{max_val}之间的小数。"))
                    continue
                if user_input == '.':
                    return dft
                if user_input == '':
                    return dft
                value = float(user_input)
                if value < min_val:
                    print(Fore.RED + f"数值不能小于 {min_val}")
                    continue
                if value > max_val:
                    print(Fore.RED + f"数值不能大于 {max_val}")
                    continue
                return value
            except ValueError:
                print(Fore.RED + "请输入有效的数字")
            except (KeyboardInterrupt, EOFError):
                print(Fore.YELLOW + "\n用户中断输入，已退出。")
                sys.exit(0)

def recommend_config(base_config: Optional[Config] = None) -> Config:
    """智能分析目录，推荐最优配置"""
    config = base_config or Config()
    dirs = config.directory if isinstance(config.directory, list) else [config.directory]
    video_files = []
    sizes = []
    for d in dirs:
        for ext in config.supported_video_formats:
            for f in glob.glob(str(Path(d)/f'**/*{ext}'), recursive=True):
                try:
                    size = os.path.getsize(f)
                    sizes.append(size)
                    video_files.append(f)
                except Exception:
                    continue
    file_count = len(video_files)
    avg_size = statistics.mean(sizes) if sizes else 0
    max_workers = min(multiprocessing.cpu_count(), 8) if file_count > 100 else 4
    if avg_size > 2*1024*1024*1024:  # 平均大于2GB
        image_compression_ratio = 0.6
        max_image_size_kb = 150
    elif avg_size > 500*1024*1024:
        image_compression_ratio = 0.7
        max_image_size_kb = 180
    else:
        image_compression_ratio = 0.8
        max_image_size_kb = 200
    # 推荐过滤规则
    file_include_patterns = None
    if file_count > 500:
        file_include_patterns = ['*.mp4', '*.mkv']
    # 推荐日志级别
    log_level = 'INFO' if file_count < 1000 else 'WARNING'
    return Config(
        directory=dirs,
        poster_suffix=config.poster_suffix,
        fanart_suffix=config.fanart_suffix,
        supported_video_formats=config.supported_video_formats,
        ignored_extensions=config.ignored_extensions,
        max_image_size_kb=max_image_size_kb,
        image_compression_ratio=image_compression_ratio,
        base64_line_length=config.base64_line_length,
        log_level=log_level,
        overwrite_existing=config.overwrite_existing,
        delete_existing_vsmeta=config.delete_existing_vsmeta,
        max_workers=max_workers,
        enable_backup=config.enable_backup,
        retry_attempts=config.retry_attempts,
        retry_delay=config.retry_delay,
        file_include_patterns=file_include_patterns,
        file_regex=config.file_regex,
        process_mode=config.process_mode,
        progress_style=config.progress_style
    )

def interactive_config_with_validation() -> Config:
    """带验证的交互式配置（支持多目录和过滤+智能推荐）"""
    while True:
        print("=== NFO to VSMETA 转换器配置 ===")
        print("请按照提示输入配置信息，按回车使用默认值。\n")
        print(f"{Fore.LIGHTGREEN_EX}0. 🌟 智能推荐配置（自动分析并推荐最优参数）{Style.RESET_ALL}")
        print(f"{Fore.LIGHTCYAN_EX}1. 手动自定义配置{Style.RESET_ALL}\n")
        mode = input(f"{Fore.CYAN}请选择配置方式（0=推荐，1=自定义，回车默认推荐）:{Style.RESET_ALL} ").strip()
        if mode == '' or mode == '0':
            print(f"{Fore.LIGHTYELLOW_EX}正在分析目录并生成推荐配置...{Style.RESET_ALL}")
            rec = recommend_config()
            print(f"\n{Fore.LIGHTGREEN_EX}推荐配置如下：{Style.RESET_ALL}")
            for field in rec.__dataclass_fields__:
                print(f"{Fore.LIGHTYELLOW_EX}{field}{Style.RESET_ALL}: {Fore.CYAN}{getattr(rec, field)}{Style.RESET_ALL}")
            accept = input(f"\n{Fore.GREEN}是否采纳推荐配置？(Y/n): {Style.RESET_ALL}").strip().lower()
            if accept in ('', 'y', 'yes'):
                return rec
            else:
                print(f"{Fore.LIGHTCYAN_EX}进入手动自定义配置...{Style.RESET_ALL}\n")
        # 手动自定义配置（原有流程）
        config = Config()
        ic = InteractiveConfig()
        dir_input = ic.get_user_input(
            "请输入要处理的目录路径（支持多个目录，用逗号、分号或空格分隔）",
            config.directory if isinstance(config.directory, str) else ','.join(config.directory)
        )
        if any(sep in dir_input for sep in [',', ';', ' '] ):
            config.directory = [d.strip() for d in re.split(r'[;,\s]+', dir_input) if d.strip()]
        else:
            config.directory = [dir_input.strip()]
        config.poster_suffix = ic.get_user_input("请输入海报文件后缀", config.poster_suffix)
        config.fanart_suffix = ic.get_user_input("请输入背景图片文件后缀", config.fanart_suffix)
        patterns = ic.get_user_input("文件名通配符过滤（如 *.mp4,*.mkv，留空为全部）", '')
        config.file_include_patterns = [p.strip() for p in patterns.split(',') if p.strip()] if patterns else None
        regex = ic.get_user_input("文件名正则过滤（如 .*1080p.*，留空为全部）", '')
        config.file_regex = regex if regex else None
        config.max_image_size_kb = ic.get_number("请输入最大图片大小(KB)", config.max_image_size_kb, 10, 1000)
        config.image_compression_ratio = ic.get_float("请输入图片压缩比例", config.image_compression_ratio, 0.1, 1.0)
        config.overwrite_existing = ic.get_yes_no("是否覆盖已存在的VSMETA文件", config.overwrite_existing)
        config.delete_existing_vsmeta = ic.get_yes_no("是否删除已存在的VSMETA文件", config.delete_existing_vsmeta)
        config.enable_backup = ic.get_yes_no("是否启用文件备份", config.enable_backup)
        config.max_workers = ic.get_number("请输入线程数", config.max_workers, 1, 16)
        config.retry_attempts = ic.get_number("请输入重试次数", config.retry_attempts, 0, 10)
        config.retry_delay = ic.get_float("请输入重试延迟(秒)", config.retry_delay, 0.1, 10.0)
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        print("\n日志级别选项:")
        for i, level in enumerate(log_levels, 1):
            print(f"{i}. {level}")
        while True:
            try:
                choice = int(ic.get_user_input("请选择日志级别", "2"))
                if 1 <= choice <= len(log_levels):
                    config.log_level = log_levels[choice - 1]
                    break
                else:
                    print(f"请输入 1-{len(log_levels)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
        errors = ConfigValidator.validate_config(config)
        if not errors:
            return config
        print("\n配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        print("请重新配置\n")

class NFOToVSMETAConverter:
    """NFO到VSMETA转换器 - 完全优化版（含详细日志与报告）"""
    
    def __init__(self, config: Config):
        self.config = config
        self.stats = ConversionStats()
        self.lock = threading.Lock()  # 线程安全计数器
        self.checkpoint_file = "conversion_checkpoint.pkl"
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, f"convert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.report_details = []  # 每个文件的处理详情
        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
    
    def load_checkpoint(self):
        """加载断点"""
        try:
            with open(self.checkpoint_file, 'rb') as f:
                self.stats.processed_files = pickle.load(f)
            logger.info(f"加载断点，已处理 {len(self.stats.processed_files)} 个文件")
        except FileNotFoundError:
            pass
    
    def save_checkpoint(self):
        """保存断点"""
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(self.stats.processed_files, f)
    
    def backup_vsmeta_file(self, vsmeta_path: str) -> Optional[str]:
        """备份VSMETA文件"""
        if not self.config.enable_backup:
            return None
            
        if os.path.exists(vsmeta_path):
            backup_dir = "backup_vsmeta"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(vsmeta_path)
            backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
            
            shutil.copy2(vsmeta_path, backup_path)
            logger.info(f"已备份: {backup_path}")
            return backup_path
        return None
    
    def detect_video_files(self, directory: Union[str, List[str]]) -> List[Tuple[str, str]]:
        """智能检测视频文件，支持多目录、通配符和正则过滤"""
        video_files = []
        supported_formats = set(self.config.supported_video_formats)
        dirs = directory if isinstance(directory, list) else [directory]
        for root_dir in dirs:
            for root, dirs_, files in os.walk(root_dir):
                dirs_[:] = [d for d in dirs_ if '@eaDir' not in d]
                for filename in files:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in supported_formats:
                        # 文件名过滤
                        if self.config.file_include_patterns:
                            if not any(fnmatch.fnmatch(filename, pat) for pat in self.config.file_include_patterns):
                                continue
                        if self.config.file_regex:
                            if not re.search(self.config.file_regex, filename):
                                continue
                        # 文件大小过滤
                        if self.config.min_size is not None:
                            file_path = os.path.join(root, filename)
                            try:
                                if os.path.getsize(file_path) < self.config.min_size:
                                    continue
                            except Exception:
                                continue
                        video_name = os.path.splitext(filename)[0]
                        nfo_path = os.path.join(root, video_name + '.nfo')
                        if os.path.exists(nfo_path):
                            video_files.append((root, filename))
                        else:
                            logger.debug(f"视频文件缺少NFO: {filename}")
        return video_files
    
    def process_directory_parallel(self) -> None:
        """并行处理目录，支持多线程/多进程切换，进度条美化，速度曲线"""
        logger.info(f"开始处理目录: {self.config.directory}，模式: {self.config.process_mode}")
        dirs = self.config.directory if isinstance(self.config.directory, list) else [self.config.directory]
        for d in dirs:
            if not os.path.exists(d):
                logger.error(f"目录不存在: {d}")
                return
        video_files = self.detect_video_files(self.config.directory)
        self.stats.total_files = len(video_files)
        if self.stats.total_files == 0:
            logger.warning("未找到可处理的视频文件")
            return
        logger.info(f"找到 {self.stats.total_files} 个视频文件")
        if self.stats.processed_files:
            video_files = [(root, filename) for root, filename in video_files 
                          if f"{root}_{filename}" not in self.stats.processed_files]
            logger.info(f"跳过已处理的 {self.stats.total_files - len(video_files)} 个文件")
        self.stats.start_time = datetime.now()
        speed_history = []
        processed_count = 0
        last_time = time.time()
        interval = 2  # 统计间隔秒
        def update_speed():
            nonlocal processed_count, last_time
            now = time.time()
            elapsed = now - last_time
            if elapsed >= interval:
                speed_history.append(processed_count / elapsed)
                processed_count = 0
                last_time = now
        def get_bar_format():
            style = self.config.progress_style
            if style == 'rocket':
                return '{l_bar}{bar} 🚀| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}, {postfix}]'
            elif style == 'rainbow':
                return '{l_bar}{bar}| 🌈{n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}, {postfix}]'
            else:
                return '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}, {postfix}]'
        if HAS_TQDM:
            bar_desc = f"{'🧵线程' if self.config.process_mode=='thread' else '⚡进程'} 处理中"
            bar_format = get_bar_format()
            with tqdm(total=len(video_files), desc=bar_desc, ncols=80, bar_format=bar_format) as pbar:
                if self.config.process_mode == 'process':
                    # 由于实例方法及lambda不可被pickle，进程模式在此回退为线程模式，避免崩溃
                    logger.warning("进程模式在当前实现中不可用，已自动回退为线程模式。")
                    self.config.process_mode = 'thread'
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                        futures = []
                        for root, filename in video_files:
                            future = executor.submit(self._process_video_file_with_progress, root, filename, pbar)
                            futures.append(future)
                        for _ in concurrent.futures.as_completed(futures):
                            processed_count += 1
                            update_speed()
                            pbar.set_postfix({"速度": f"{speed_history[-1]:.1f}/s" if speed_history else ''})
                else:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                        futures = []
                        for root, filename in video_files:
                            future = executor.submit(self._process_video_file_with_progress, root, filename, pbar)
                            futures.append(future)
                        for f in concurrent.futures.as_completed(futures):
                            processed_count += 1
                            update_speed()
                            pbar.set_postfix({"速度": f"{speed_history[-1]:.1f}/s" if speed_history else ''})
        else:
            print(f"开始处理 {len(video_files)} 个文件...")
            if self.config.process_mode == 'process':
                logger.warning("进程模式在当前实现中不可用，已自动回退为线程模式。")
                self.config.process_mode = 'thread'
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    futures = [executor.submit(self._process_video_file, root, filename)
                              for root, filename in video_files]
                    for _ in concurrent.futures.as_completed(futures):
                        processed_count += 1
                        update_speed()
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                    futures = [executor.submit(self._process_video_file, root, filename) 
                              for root, filename in video_files]
                    for f in concurrent.futures.as_completed(futures):
                        processed_count += 1
                        update_speed()
        self.stats.end_time = datetime.now()
        self.print_final_stats()
        # 输出速度曲线和性能分析
        if speed_history:
            print(f"\n{Fore.CYAN}处理速度历史曲线:{Style.RESET_ALL}")
            for i, spd in enumerate(speed_history, 1):
                bar = '█' * int(spd * 2)
                print(f"{i*interval:>3}s: {bar} {spd:.2f} 文件/秒")
            avg = sum(speed_history)/len(speed_history)
            fastest = max(speed_history)
            slowest = min(speed_history)
            print(f"{Fore.MAGENTA}平均速度: {avg:.2f} 文件/秒  最快: {fastest:.2f}  最慢: {slowest:.2f}{Style.RESET_ALL}")
        self._last_speed_history = speed_history  # 保存供导出
        self._last_speed_interval = interval
    
    def _process_video_file_with_progress(self, root: str, filename: str, pbar) -> None:
        """带进度条的文件处理"""
        try:
            self._process_video_file(root, filename)
            pbar.set_postfix({
                "成功": self.stats.success_count, 
                "失败": self.stats.error_count,
                "跳过": self.stats.skipped_count
            })
        except Exception as e:
            logger.error(f"处理文件失败: {e}")
        finally:
            pbar.update(1)
    
    def _process_video_file(self, root: str, filename: str) -> None:
        """处理单个视频文件，记录详细日志"""
        video_name = os.path.splitext(filename)[0]
        vsmeta_path = os.path.join(root, filename + '.vsmeta')
        file_key = f"{root}_{filename}"
        start_time = datetime.now()
        detail = {
            'file': filename,
            'dir': root,
            'start': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'result': '',
            'error': '',
            'duration': 0
        }
        # 检查是否已处理
        if file_key in self.stats.processed_files:
            with self.lock:
                self.stats.skipped_count += 1
            detail['result'] = 'skipped'
            detail['duration'] = 0
            self.log_detail(detail)
            return
        # 检查是否已存在VSMETA文件
        if os.path.exists(vsmeta_path):
            if self.config.delete_existing_vsmeta:
                try:
                    self.backup_vsmeta_file(vsmeta_path)
                    os.remove(vsmeta_path)
                    logger.info(f"删除现有VSMETA文件: {vsmeta_path}")
                except Exception as e:
                    logger.error(f"删除VSMETA文件失败: {e}")
                    detail['result'] = 'delete_failed'
                    detail['error'] = str(e)
                    detail['duration'] = (datetime.now() - start_time).total_seconds()
                    self.log_detail(detail)
                    return
            elif not self.config.overwrite_existing:
                logger.debug(f"VSMETA文件已存在，跳过: {vsmeta_path}")
                with self.lock:
                    self.stats.skipped_count += 1
                detail['result'] = 'skipped_exists'
                detail['duration'] = 0
                self.log_detail(detail)
                return
        nfo_path = os.path.join(root, video_name + '.nfo')
        poster_path = os.path.join(root, video_name + self.config.poster_suffix)
        fanart_path = os.path.join(root, video_name + self.config.fanart_suffix)
        if os.path.exists(nfo_path):
            try:
                doc = xmldom.parse(nfo_path)
                fallback = self.ai_fill_metadata_by_filename(filename, root)
                metadata = self._extract_metadata(doc, fallback)
                self._generate_and_write_vsmeta(metadata, vsmeta_path, poster_path, fanart_path)
                with self.lock:
                    self.stats.success_count += 1
                    self.stats.processed_files.add(file_key)
                logger.info(f"成功转换: {nfo_path}")
                detail['result'] = 'success'
                if metadata.get('_ai_filled'):
                    detail['result'] = 'success_ai_filled'
            except Exception as e:
                with self.lock:
                    self.stats.error_count += 1
                logger.error(f"转换失败 {nfo_path}: {e}")
                detail['result'] = 'error'
                detail['error'] = str(e)
        else:
            # NFO缺失，尝试AI补全
            try:
                metadata = self.ai_fill_metadata_by_filename(filename, root)
                self._generate_and_write_vsmeta(metadata, vsmeta_path, poster_path, fanart_path)
                with self.lock:
                    self.stats.success_count += 1
                    self.stats.processed_files.add(file_key)
                logger.info(f"AI补全生成VSMETA: {vsmeta_path}")
                detail['result'] = 'ai_filled_nfo_missing'
            except Exception as e:
                with self.lock:
                    self.stats.error_count += 1
                logger.warning(f"NFO缺失且AI补全失败: {filename}: {e}")
                detail['result'] = 'nfo_missing'
                detail['error'] = str(e)
        detail['duration'] = (datetime.now() - start_time).total_seconds()
        self.log_detail(detail)
    
    def ai_fill_metadata_by_filename(self, filename: str, root: str) -> dict:
        """根据文件名和目录智能补全元数据"""
        name = os.path.splitext(filename)[0]
        # 例: 片名.2020.1080p.XX.mkv
        m = re.match(r'([\u4e00-\u9fa5A-Za-z0-9_\- ]+)[. _-]+(\d{4})', name)
        if m:
            title = m.group(1).replace('_', ' ').replace('.', ' ').strip()
            year = int(m.group(2))
        else:
            title = name.replace('_', ' ').replace('.', ' ').strip()
            year = 1900
        # 简单推断类型
        genre = []
        if re.search(r'动画|anime|cartoon', name, re.I):
            genre.append('动画')
        if re.search(r'action|动作', name, re.I):
            genre.append('动作')
        if re.search(r'comedy|喜剧', name, re.I):
            genre.append('喜剧')
        # 目录名作为补充
        dir_name = os.path.basename(root)
        if not genre and re.search(r'动画|anime|cartoon', dir_name, re.I):
            genre.append('动画')
        return {
            'title': title,
            'sorttitle': title,
            'tagline': '',
            'plot': f'（AI补全）{title}，年份{year}',
            'year': year,
            'level': 'G',
            'date': f'{year}-01-01',
            'rate': 0.0,
            'genre': genre,
            'actors': [],
            'directors': [],
            'writers': [],
            '_ai_filled': True
        }
    
    def _extract_metadata(self, doc: xmldom.Document, fallback: Optional[dict] = None) -> Dict[str, Union[str, List[str], int, float]]:
        """从XML文档中提取元数据，缺失时用AI补全"""
        meta = {
            'title': self._get_node(doc, 'title', ''),
            'sorttitle': self._get_node(doc, 'sorttitle', ''),
            'tagline': self._get_node(doc, 'tagline', ''),
            'plot': self._get_node(doc, 'plot', ''),
            'year': int(self._get_node(doc, 'year', '1900')),
            'level': self._get_node(doc, 'mpaa', 'G'),
            'date': self._get_node(doc, 'premiered', '1900-01-01'),
            'rate': float(self._get_node(doc, 'rating', '0')),
            'genre': self._get_node_list(doc, 'genre'),
            'actors': self._get_node_list(doc, 'actor', 'name'),
            'directors': self._get_node_list(doc, 'director'),
            'writers': self._get_node_list(doc, 'writer'),
        }
        # 检查关键字段缺失，尝试AI补全
        if not meta['title'] or meta['year'] == 1900 or not meta['plot']:
            if fallback:
                for k in meta:
                    if (not meta[k] or (k == 'year' and meta[k] == 1900)) and k in fallback:
                        meta[k] = fallback[k]
                meta['_ai_filled'] = True
        return meta
    
    def _generate_vsmeta_data(self, metadata: dict, poster_path: str, fanart_path: str) -> bytes:
        """生成VSMETA二进制数据"""
        buf, group = bytearray(), bytearray()
        
        # 写入基本信息
        self._write_byte(buf, 0x08)
        self._write_byte(buf, 0x01)
        
        self._write_byte(buf, 0x12)
        self._write_string(buf, metadata['title'])
        
        self._write_byte(buf, 0x1A)
        self._write_string(buf, metadata['sorttitle'] or metadata['title'])
        
        self._write_byte(buf, 0x22)
        self._write_string(buf, metadata['tagline'] or metadata['title'])
        
        self._write_byte(buf, 0x28)
        self._write_int(buf, int(metadata['year']))
        
        self._write_byte(buf, 0x32)
        self._write_string(buf, metadata['date'])
        
        self._write_byte(buf, 0x38)
        self._write_byte(buf, 0x01)
        
        self._write_byte(buf, 0x42)
        self._write_string(buf, metadata['plot'])
        
        self._write_byte(buf, 0x4A)
        self._write_string(buf, 'null')
        
        # 写入演员、导演、类型、编剧信息
        for actor in metadata['actors']:
            self._write_byte(group, 0x0A)
            self._write_string(group, actor)
        
        for director in metadata['directors']:
            self._write_byte(group, 0x12)
            self._write_string(group, director)
        
        for genre in metadata['genre']:
            self._write_byte(group, 0x1A)
            self._write_string(group, genre)
        
        for writer in metadata['writers']:
            self._write_byte(group, 0x22)
            self._write_string(group, writer)
        
        self._write_byte(buf, 0x52)
        self._write_int(buf, len(group))
        buf.extend(group)
        group.clear()
        
        # 写入分级和评分
        self._write_byte(buf, 0x5A)
        self._write_string(buf, metadata['level'])
        
        self._write_byte(buf, 0x60)
        self._write_int(buf, int(float(metadata['rate']) * 10))
        
        # 处理海报图片
        if os.path.exists(poster_path):
            self._add_image_to_buffer(buf, poster_path, 0x8A, 0x92)
        
        # 处理背景图片
        if os.path.exists(fanart_path):
            self._add_fanart_to_buffer(buf, group, fanart_path, 0xAA)
        
        return bytes(buf)
    
    def _add_image_to_buffer(self, buf: bytearray, image_path: str, start_byte: int, md5_byte: int) -> None:
        """添加图片到缓冲区"""
        try:
            self._write_byte(buf, start_byte)
            self._write_byte(buf, 0x01)
            
            image_base64 = self._image_to_base64(image_path)
            image_md5 = self._to_md5(image_base64)
            
            self._write_string(buf, image_base64)
            self._write_byte(buf, md5_byte)
            self._write_byte(buf, 0x01)
            self._write_string(buf, image_md5)
        except Exception as e:
            logger.warning(f"处理图片失败 {image_path}: {e}")
    
    def _add_fanart_to_buffer(self, buf: bytearray, group: bytearray, fanart_path: str, start_byte: int) -> None:
        """添加背景图片到缓冲区"""
        try:
            self._write_byte(buf, start_byte)
            self._write_byte(buf, 0x01)
            
            fanart_base64 = self._image_to_base64(fanart_path)
            fanart_md5 = self._to_md5(fanart_base64)
            
            self._write_byte(group, 0x0A)
            self._write_string(group, fanart_base64)
            self._write_byte(group, 0x12)
            self._write_string(group, fanart_md5)
            self._write_byte(group, 0x18)
            self._write_int(group, int(time.time()))
            
            self._write_int(buf, len(group))
            buf.extend(group)
            group.clear()
        except Exception as e:
            logger.warning(f"处理背景图片失败 {fanart_path}: {e}")

    # 工具方法
    def _write_byte(self, ba: bytearray, value: int) -> None:
        """写入字节"""
        ba.extend(bytes([value]))

    def _write_string(self, ba: bytearray, string: str) -> None:
        """写入字符串"""
        byte_data = string.encode('utf-8')
        length = len(byte_data)
        self._write_int(ba, length)
        ba.extend(byte_data)

    def _write_int(self, ba: bytearray, value: int) -> None:
        """写入整数（变长编码）"""
        while value > 128:
            self._write_byte(ba, value % 128 + 128)
            value = value // 128
        self._write_byte(ba, value)

    def _get_node(self, doc_or_elem, tag: str, default: str = ' ') -> str:
        """获取XML节点值，兼容Document和Element"""
        nodes = doc_or_elem.getElementsByTagName(tag)
        if len(nodes) < 1 or not nodes[0].hasChildNodes() or nodes[0].firstChild is None:
            return default
        return nodes[0].firstChild.nodeValue or default

    def _get_node_list(self, doc_or_elem, tag: str, child_tag: str = '', default: Optional[List[str]] = None) -> List[str]:
        """获取XML节点列表，兼容Document和Element"""
        if default is None:
            default = []
        nodes = doc_or_elem.getElementsByTagName(tag)
        if len(nodes) < 1:
            return default
        if not child_tag:
            return [node.firstChild.nodeValue or '' for node in nodes if node.firstChild is not None]
        else:
            return [self._get_node(node, child_tag, '') for node in nodes]

    def _image_to_base64(self, image_path: str) -> str:
        """将图片转换为Base64编码"""
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # 无 Pillow 时直接编码
        if not HAS_PIL:
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
        else:
            compressed_image = self._compress_image_optimized(image_bytes)
            base64_string = compressed_image.decode('utf-8')

        # 按指定长度分割
        lines = [base64_string[i:i+self.config.base64_line_length] 
                for i in range(0, len(base64_string), self.config.base64_line_length)]
        return '\n'.join(lines)

    def _compress_image_optimized(self, image_bytes: bytes) -> bytes:
        """优化的图片压缩，减少内存使用；Pillow 不可用时直接返回原图编码。"""
        if not HAS_PIL:
            return base64.b64encode(image_bytes)
        try:
            with io.BytesIO(image_bytes) as source:
                original_kb = len(image_bytes) // 1024
                if original_kb <= self.config.max_image_size_kb:
                    return base64.b64encode(image_bytes)

                with Image.open(source) as img:
                    img_format = (img.format or 'JPEG')
                    ratio = self.config.image_compression_ratio

                    # 逐步缩放与降低质量
                    while ratio >= 0.1:
                        new_w = max(1, int(img.width * ratio))
                        new_h = max(1, int(img.height * ratio))
                        with io.BytesIO() as output:
                            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            quality = max(10, int(95 * ratio))
                            try:
                                resized.save(output, format=img_format, quality=quality, optimize=True)
                            except Exception:
                                resized.save(output, format='JPEG', quality=quality, optimize=True)
                            compressed = output.getvalue()
                        if len(compressed) // 1024 <= self.config.max_image_size_kb:
                            return base64.b64encode(compressed)
                        ratio -= 0.1

                    # 最后保底再压一次到极限
                    with io.BytesIO() as output:
                        resized = img.resize((max(1, img.width // 10), max(1, img.height // 10)), Image.Resampling.LANCZOS)
                        resized.save(output, format='JPEG', quality=10)
                        return base64.b64encode(output.getvalue())
        except Exception as e:
            logger.warning(f"图片压缩失败，已使用原图编码: {e}")
            return base64.b64encode(image_bytes)

    def _to_md5(self, text: str) -> str:
        """生成MD5哈希值"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()
    
    def print_final_stats(self):
        """打印最终统计信息（美化+emoji+对齐）"""
        print(f"\n{Fore.CYAN}{'='*30}\n{Style.BRIGHT}转换完成统计{Style.RESET_ALL}\n{'='*30}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ 总文件数 : {self.stats.total_files:>6}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ 成功     : {self.stats.success_count:>6}{Style.RESET_ALL}")
        print(f"{Fore.RED}❌ 失败     : {self.stats.error_count:>6}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚠️ 跳过     : {self.stats.skipped_count:>6}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}📈 成功率   : {self.stats.success_rate:>6.1f}%{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}⏱️ 总耗时   : {self.stats.duration:>6.1f} 秒{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🚀 处理速度 : {self.stats.processing_speed:>6.1f} 文件/秒{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'='*30}{Style.RESET_ALL}")
    
    def process_with_checkpoint(self):
        """处理目录并支持断点续传"""
        try:
            self.load_checkpoint()
            self.process_directory_parallel()
        except KeyboardInterrupt:
            logger.info("用户中断处理")
            self.save_checkpoint()
            self.print_final_stats()
        except Exception as e:
            logger.error(f"处理过程出错: {e}")
            self.save_checkpoint()
            raise
        finally:
            if os.path.exists(self.checkpoint_file):
                try:
                    os.remove(self.checkpoint_file)
                    logger.debug("清理断点文件")
                except:
                    pass

    def log_detail(self, detail: dict):
        """记录处理详情"""
        self.report_details.append(detail)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(detail, ensure_ascii=False) + '\n')

    def export_report(self, fmt='txt'):
        """导出处理报告
        支持格式：txt, csv, json, html
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.{fmt}"
        
        # 添加汇总信息
        summary = {
            "开始时间": self.stats.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.stats.start_time else "",
            "结束时间": self.stats.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.stats.end_time else "",
            "总文件数": self.stats.total_files,
            "成功数": self.stats.success_count,
            "失败数": self.stats.error_count,
            "跳过数": self.stats.skipped_count,
            "成功率": f"{self.stats.success_rate:.1f}%",
            "处理时长": f"{self.stats.duration:.1f}秒",
            "处理速度": f"{self.stats.processing_speed:.2f}个/秒"
        }
        
        if fmt == 'txt':
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== NFO to VSMETA 转换报告 ===\n\n")
                f.write("统计信息:\n")
                for k, v in summary.items():
                    f.write(f"{k}: {v}\n")
                f.write("\n详细信息:\n")
                for detail in self.report_details:
                    f.write(f"\n文件: {detail['file']}\n")
                    f.write(f"目录: {detail['dir']}\n")
                    f.write(f"开始时间: {detail['start']}\n")
                    f.write(f"结果: {detail['result']}\n")
                    if detail['error']:
                        f.write(f"错误: {detail['error']}\n")
                    f.write(f"耗时: {detail['duration']:.2f}秒\n")
        
        elif fmt == 'csv':
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['文件名', '目录', '开始时间', '结果', '错误信息', '耗时(秒)'])
                for detail in self.report_details:
                    writer.writerow([
                        detail['file'],
                        detail['dir'],
                        detail['start'],
                        detail['result'],
                        detail['error'],
                        f"{detail['duration']:.2f}"
                    ])
        
        elif fmt == 'json':
            report = {
                'summary': summary,
                'details': self.report_details
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        elif fmt == 'html':
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>NFO to VSMETA 转换报告</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .success {{ color: green; }}
                    .error {{ color: red; }}
                    .warning {{ color: orange; }}
                </style>
            </head>
            <body>
                <h1>NFO to VSMETA 转换报告</h1>
                <h2>统计信息</h2>
                <table>
                    <tr><th>项目</th><th>数值</th></tr>
                    {''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in summary.items())}
                </table>
                <h2>详细信息</h2>
                <table>
                    <tr>
                        <th>文件名</th>
                        <th>目录</th>
                        <th>开始时间</th>
                        <th>结果</th>
                        <th>错误信息</th>
                        <th>耗时(秒)</th>
                    </tr>
                    {''.join(f'''
                    <tr class="{self._get_result_class(d['result'])}">
                        <td>{d['file']}</td>
                        <td>{d['dir']}</td>
                        <td>{d['start']}</td>
                        <td>{d['result']}</td>
                        <td>{d['error']}</td>
                        <td>{d['duration']:.2f}</td>
                    </tr>
                    ''' for d in self.report_details)}
                </table>
            </body>
            </html>
            """
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        logger.info(f"报告已导出到: {filename}")
        return filename

    def _get_result_class(self, result: str) -> str:
        """获取结果的CSS类名"""
        if result in ['success', 'success_ai_filled', 'ai_filled_nfo_missing']:
            return 'success'
        elif result in ['error', 'delete_failed']:
            return 'error'
        else:
            return 'warning'


    def export_performance_report(self, fmt='txt'):
        """导出性能分析报告，支持txt/csv"""
        speed_history = getattr(self, '_last_speed_history', None)
        interval = getattr(self, '_last_speed_interval', 2)
        if not speed_history:
            print(Fore.YELLOW + "暂无可导出的性能分析数据。请先运行一次转换。")
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        if fmt == 'txt':
            path = f'performance_{ts}.txt'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"性能分析报告\n{'='*30}\n")
                f.write("区间(s)\t速度(文件/秒)\n")
                for i, spd in enumerate(speed_history, 1):
                    f.write(f"{i*interval:>3}\t{spd:.2f}\n")
                avg = sum(speed_history)/len(speed_history)
                fastest = max(speed_history)
                slowest = min(speed_history)
                f.write(f"\n平均速度: {avg:.2f}\n最快: {fastest:.2f}\n最慢: {slowest:.2f}\n")
            print(Fore.GREEN + f"TXT性能报告已导出: {path}")
        elif fmt == 'csv':
            path = f'performance_{ts}.csv'
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['区间(s)', '速度(文件/秒)'])
                for i, spd in enumerate(speed_history, 1):
                    writer.writerow([i*interval, f"{spd:.2f}"])
                avg = sum(speed_history)/len(speed_history)
                fastest = max(speed_history)
                slowest = min(speed_history)
                writer.writerow([])
                writer.writerow(['平均速度', avg])
                writer.writerow(['最快', fastest])
                writer.writerow(['最慢', slowest])
            print(Fore.GREEN + f"CSV性能报告已导出: {path}")
        else:
            print(Fore.RED + "不支持的性能报告格式。")

    def export_smart_analysis_report(self, fmt='txt'):
        """导出智能分析报告，支持txt/csv/html"""
        if not self.report_details:
            print(Fore.YELLOW + "暂无可导出的分析数据。")
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        details = self.report_details
        # 失败原因分布
        reason_count = {}
        for d in details:
            reason = d['result']
            reason_count[reason] = reason_count.get(reason, 0) + 1
        # 耗时TOP
        sorted_by_time = sorted(details, key=lambda d: d['duration'], reverse=True)
        top5 = sorted_by_time[:5]
        # 成功率
        total = len(details)
        success = sum(1 for d in details if d['result'] == 'success')
        fail = sum(1 for d in details if d['result'] == 'error')
        skip = sum(1 for d in details if d['result'].startswith('skip'))
        success_rate = (success / total * 100) if total else 0
        # 建议
        advice = []
        if fail > 0:
            advice.append("部分文件转换失败，建议检查NFO格式或图片文件是否损坏。")
        if reason_count.get('nfo_missing', 0) > 0:
            advice.append("有视频缺少NFO文件，建议补全NFO。")
        if reason_count.get('delete_failed', 0) > 0:
            advice.append("部分VSMETA删除失败，建议检查文件权限。")
        if success_rate < 80:
            advice.append("成功率较低，建议适当调整配置或排查异常文件。")
        if not advice:
            advice.append("整体运行良好，无明显异常。")
        # 导出
        if fmt == 'txt':
            path = f'smart_analysis_{ts}.txt'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"智能分析报告\n{'='*30}\n")
                f.write(f"总文件数: {total}\n成功: {success}\n失败: {fail}\n跳过: {skip}\n成功率: {success_rate:.1f}%\n\n")
                f.write("失败原因分布:\n")
                for k, v in reason_count.items():
                    f.write(f"  {k}: {v} 个\n")
                f.write("\n耗时TOP5文件:\n")
                for d in top5:
                    f.write(f"  {d['file']}\t{d['dir']}\t{d['duration']:.2f}s\t{d['result']}\n")
                f.write("\n建议:\n")
                for adv in advice:
                    f.write(f"- {adv}\n")
            print(Fore.GREEN + f"智能分析TXT报告已导出: {path}")
        elif fmt == 'csv':
            path = f'smart_analysis_{ts}.csv'
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['类型', '内容'])
                writer.writerow(['总文件数', total])
                writer.writerow(['成功', success])
                writer.writerow(['失败', fail])
                writer.writerow(['跳过', skip])
                writer.writerow(['成功率', f"{success_rate:.1f}%"])
                writer.writerow([])
                writer.writerow(['失败原因分布', ''])
                for k, v in reason_count.items():
                    writer.writerow([k, v])
                writer.writerow([])
                writer.writerow(['耗时TOP5文件', ''])
                for d in top5:
                    writer.writerow([d['file'], d['dir'], f"{d['duration']:.2f}s", d['result']])
                writer.writerow([])
                writer.writerow(['建议', ''])
                for adv in advice:
                    writer.writerow([adv])
            print(Fore.GREEN + f"智能分析CSV报告已导出: {path}")
        elif fmt == 'html':
            path = f'smart_analysis_{ts}.html'
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<html><head><meta charset="utf-8"><title>智能分析报告</title></head><body>')
                f.write('<h2>智能分析报告</h2>')
                f.write(f'<p>总文件数: {total} | 成功: {success} | 失败: {fail} | 跳过: {skip} | 成功率: {success_rate:.1f}%</p>')
                f.write('<h3>失败原因分布</h3><ul>')
                for k, v in reason_count.items():
                    f.write(f'<li>{k}: {v} 个</li>')
                f.write('</ul><h3>耗时TOP5文件</h3><ol>')
                for d in top5:
                    f.write(f'<li>{d["file"]} | {d["dir"]} | {d["duration"]:.2f}s | {d["result"]}</li>')
                f.write('</ol><h3>建议</h3><ul>')
                for adv in advice:
                    f.write(f'<li>{adv}</li>')
                f.write('</ul></body></html>')
            print(Fore.GREEN + f"智能分析HTML报告已导出: {path}")
        else:
            print(Fore.RED + "不支持的报告格式。")

    def _generate_and_write_vsmeta(self, metadata: dict, vsmeta_path: str, poster_path: str, fanart_path: str) -> None:
        """生成并写入VSMETA文件（支持AI补全元数据）"""
        vsmeta_data = self._generate_vsmeta_data(metadata, poster_path, fanart_path)
        with open(vsmeta_path, 'wb') as f:
            f.write(vsmeta_data)

    def analyze_error_and_suggest(self, detail: dict) -> str:
        """根据失败详情分析原因并给出修复建议"""
        err = detail.get('error', '')
        result = detail.get('result', '')
        if result == 'nfo_missing':
            return '缺少NFO文件，建议补全NFO或启用AI补全。'
        if result == 'delete_failed':
            return 'VSMETA删除失败，建议检查文件权限或是否被占用。'
        if 'parse' in err or 'XML' in err:
            return 'NFO解析失败，建议检查NFO文件格式是否正确。'
        if 'image' in err or '图片' in err:
            return '图片处理失败，建议检查图片文件是否损坏或格式不支持。'
        if 'permission' in err or '权限' in err:
            return '文件权限不足，建议以管理员身份运行或修改权限。'
        if '补全失败' in err:
            return 'AI补全失败，建议手动补全元数据。'
        if not err:
            return '未知错误，建议检查文件完整性。'
        return '建议检查错误详情：' + err

# 动画：点点点spinner
def spinner(msg, duration=2):
    for c in itertools.cycle(['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']):
        print(f"\r{Fore.LIGHTMAGENTA_EX}{msg} {c}{Style.RESET_ALL}", end='', flush=True)
        time.sleep(0.1)
        duration -= 0.1
        if duration <= 0:
            break
    print("\r", end='')

def show_menu_with_arrows(options, title="NFO to VSMETA 转换器 - 完全优化版"):
    """支持上下键选择的菜单，返回选中项索引。"""
    # 无 readchar 时的简易回退
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
        except Exception:
            return len(options)
        return len(options)

    idx = 0
    while True:
        print("\033[2J\033[H")  # 清屏
        print(f"\n{Fore.CYAN}{title}{Style.RESET_ALL}\n")
        for i, option in enumerate(options):
            if i == idx:
                print(f"{Fore.GREEN}> {option}{Style.RESET_ALL}")
            else:
                print(f"  {option}")
        
        key = readchar.readkey()
        if key == readchar.key.UP and idx > 0:
            idx -= 1
        elif key == readchar.key.DOWN and idx < len(options) - 1:
            idx += 1
        elif key in [readchar.key.ENTER, '\r', '\n']:
            return idx
        elif key in [readchar.key.CTRL_C, readchar.key.ESC]:
            raise KeyboardInterrupt
        print(f"\n{Fore.CYAN}{'🟢'*8} {Style.BRIGHT}{title}{'🟢'*8}{Style.RESET_ALL}")
        for i, opt in enumerate(options):
            prefix = '👉' if i == idx else '  '
            color = Fore.GREEN if i == idx else Fore.YELLOW
            print(f"{color}{prefix} {i+1}. {opt}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'-'*40}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}↑↓选择，回车确定，b返回，数字/q/exit/回车退出{Style.RESET_ALL}")
        key = readchar.readkey()
        if key in (readchar.key.UP, 'w', 'W'):
            idx = (idx - 1) % len(options)
        elif key in (readchar.key.DOWN, 's', 'S'):
            idx = (idx + 1) % len(options)
        elif key in ('\r', '\n'):
            return idx
        elif key in ('b', 'B'):
            return -1
        elif key in ('q', 'Q'):
            return len(options)  # 退出
        elif key.isdigit():
            num = int(key)
            if 1 <= num <= len(options):
                return num - 1

def show_config(config: Config) -> None:
    """显示当前配置"""
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
    # 详细字段回显
    print("\n=== 当前配置（所有字段） ===")
    for field in config.__dataclass_fields__:
        print(f"{field}: {getattr(config, field)}")
    print()

def parse_semantic_command(cmd: str, base_config: Optional[Config] = None) -> Config:
    """解析语义化命令"""
    config = base_config or Config()
    
    # 处理目录设置
    if "目录" in cmd or "path" in cmd.lower():
        paths = re.findall(r'"([^"]+)"', cmd)
        if paths:
            config.directory = paths if len(paths) > 1 else paths[0]
    
    # 处理图片大小
    if "图片" in cmd and "大小" in cmd:
        sizes = re.findall(r'(\d+)\s*[kK][bB]', cmd)
        if sizes:
            config.max_image_size_kb = int(sizes[0])
    
    # 处理线程数
    if "线程" in cmd:
        threads = re.findall(r'(\d+)\s*个?线程', cmd)
        if threads:
            config.max_workers = min(16, max(1, int(threads[0])))
    
    # 处理重试
    if "重试" in cmd:
        retries = re.findall(r'重试(\d+)次', cmd)
        if retries:
            config.retry_attempts = int(retries[0])
    
    # 处理日志级别
    if "日志" in cmd:
        levels = {"debug": "DEBUG", "info": "INFO", "warning": "WARNING", "error": "ERROR"}
        for k, v in levels.items():
            if k in cmd.lower():
                config.log_level = v
                break
    
    # 处理处理模式
    if "进程" in cmd:
        config.process_mode = "process"
    elif "线程" in cmd:
        config.process_mode = "thread"
    
    # 处理文件过滤
    if "过滤" in cmd:
        patterns = re.findall(r'"([^"]+)"', cmd)
        if patterns:
            if "*" in patterns[0] or "?" in patterns[0]:
                config.file_include_patterns = patterns
            else:
                config.file_regex = patterns[0]
    
    return config
    """解析自然语言命令，返回推荐Config"""
    import copy
    config = copy.deepcopy(base_config) if base_config else Config()
    cmd = cmd.lower()
    # 只处理某格式
    m = re.findall(r'(mp4|mkv|avi|ts|wmv|rmvb)', cmd)
    if m:
        config.file_include_patterns = [f'*.{ext}' for ext in m]
    # 只处理大于XGB/XMB
    m = re.search(r'大于(\d+)(g|gb|m|mb)', cmd)
    if m:
        size = int(m.group(1))
        unit = m.group(2)
        if unit.startswith('g'):
            min_size = size * 1024 * 1024 * 1024
        else:
            min_size = size * 1024 * 1024
        config.min_size = min_size  # 类型安全
    # 只处理X年以后的
    m = re.search(r'(\d{4})年以?后', cmd)
    if m:
        year = int(m.group(1))
        config.file_regex = f'.*({year+1}|{year+2}|{year+3}|{year+4}|{year+5}|{year+6}|{year+7}|{year+8}|{year+9})'
    # 线程数
    m = re.search(r'(线程数|多线程|thread)[^\d]*(\d+)', cmd)
    if m:
        config.max_workers = int(m.group(2))
    # 图片压缩到XKB
    m = re.search(r'(图片|海报|压缩)[^\d]*(\d+)[ ]*kb', cmd)
    if m:
        config.max_image_size_kb = int(m.group(2))
    # 压缩比例
    m = re.search(r'(压缩比例|压缩比)[^\d]*(0\.\d+|1\.0|1)', cmd)
    if m:
        config.image_compression_ratio = float(m.group(2))
    # 只处理包含关键词
    m = re.findall(r'只处理.*?([\u4e00-\u9fa5a-zA-Z0-9]+)', cmd)
    if m and not config.file_regex:
        config.file_regex = '|'.join(m)
    return config

def main():
    """主函数"""
    print(f"{Fore.CYAN}NFO to VSMETA 转换器 - 完全优化版{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}支持：多线程、断点续传、智能重试、AI补全{Style.RESET_ALL}\n")
    
    try:
        options = [
            "1. 🚀 开始转换（使用默认配置）",
            "2. ⚙️ 配置向导",
            "3. 📝 语义化配置",
            "4. 💡 智能推荐配置",
            "5. ❌ 退出"
        ]
        
        while True:
            choice = show_menu_with_arrows(options)
            
            if choice == 0:  # 开始转换
                converter = NFOToVSMETAConverter(Config())
                converter.process_with_checkpoint()
                
                if converter.stats.total_files > 0:
                    print("\n是否导出报告？")
                    report_options = [
                        "1. 📊 导出详细报告 (HTML)",
                        "2. 📈 导出性能报告",
                        "3. 🔍 导出智能分析报告",
                        "4. ⏭️ 跳过",
                    ]
                    report_choice = show_menu_with_arrows(report_options)
                    if report_choice == 0:
                        converter.export_report('html')
                    elif report_choice == 1:
                        converter.export_performance_report()
                    elif report_choice == 2:
                        converter.export_smart_analysis_report()
            
            elif choice == 1:  # 配置向导
                config = interactive_config_with_validation()
                show_config(config)
                if input("\n确认使用此配置开始转换？(y/N): ").lower() == 'y':
                    converter = NFOToVSMETAConverter(config)
                    converter.process_with_checkpoint()
            
            elif choice == 2:  # 语义化配置
                print("\n示例命令：")
                print("- 设置目录 \"/path/to/movies\" 和 \"/path/to/series\"")
                print("- 使用8个线程处理，图片大小限制200KB")
                print("- 过滤文件名 \"*.mkv\" 或正则 \".*1080p.*\"")
                cmd = input("\n请输入配置命令：")
                config = parse_semantic_command(cmd)
                show_config(config)
                if input("\n确认使用此配置开始转换？(y/N): ").lower() == 'y':
                    converter = NFOToVSMETAConverter(config)
                    converter.process_with_checkpoint()
            
            elif choice == 3:  # 智能推荐
                spinner("正在分析目录结构和文件特征...", 2)
                config = recommend_config()
                show_config(config)
                if input("\n使用推荐配置开始转换？(y/N): ").lower() == 'y':
                    converter = NFOToVSMETAConverter(config)
                    converter.process_with_checkpoint()
            
            elif choice == 4:  # 退出
                print(f"\n{Fore.YELLOW}感谢使用，再见！{Style.RESET_ALL}")
                break
            
            input("\n按回车键继续...")
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}程序已终止{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}发生错误: {e}{Style.RESET_ALL}")
        logger.exception("未处理的异常")
    """主函数（进一步美化+上下键菜单）"""
    parser = argparse.ArgumentParser(description='NFO to VSMETA 转换器 - 完全优化版')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    parser.add_argument('-d', '--directory', help='处理目录')
    parser.add_argument('-i', '--interactive', action='store_true', help='交互模式')
    parser.add_argument('--overwrite', action='store_true', help='覆盖已存在的文件')
    parser.add_argument('--delete-existing', action='store_true', help='删除已存在的VSMETA文件')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='日志级别')
    parser.add_argument('--workers', type=int, help='线程数')
    parser.add_argument('--no-backup', action='store_true', help='禁用备份')
    args = parser.parse_args()
    
    # 如果指定了命令行参数，直接运行
    if args.directory or args.overwrite or args.delete_existing or args.workers or args.no_backup:
        config = Config.from_file(args.config)
        if args.directory:
            config.directory = args.directory
        if args.overwrite:
            config.overwrite_existing = True
        if args.delete_existing:
            config.delete_existing_vsmeta = True
        if args.workers:
            config.max_workers = args.workers
        if args.no_backup:
            config.enable_backup = False
        config.log_level = args.log_level
        
        converter = NFOToVSMETAConverter(config)
        converter.process_with_checkpoint()
        return
    
    # 交互模式
    if args.interactive:
        config = interactive_config_with_validation()
        converter = NFOToVSMETAConverter(config)
        converter.process_with_checkpoint()
        return
    
    # 菜单模式
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
        "🤖 智能助手/语义命令",
        "❌ 退出 (q/exit/回车)"
    ]
    converter = None
    while True:
        idx = show_menu_with_arrows(menu_options)
        if idx == 12 or idx == len(menu_options):
            print(Fore.GREEN + "再见！")
            break
        elif idx == 0:
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()
        elif idx == 1:
            config = interactive_config_with_validation()
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()
        elif idx == 2:
            config_path = input(str(f"{Fore.CYAN}>> {Style.RESET_ALL}请输入配置文件路径 (默认: config.json): ")).strip()
            if not config_path:
                config_path = 'config.json'
            config = Config.from_file(config_path)
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()
        elif idx == 3:
            config_path = input(str(f"{Fore.CYAN}>> {Style.RESET_ALL}请输入保存路径 (默认: config.json): ")).strip()
            if not config_path:
                config_path = 'config.json'
            config.save_to_file(config_path)
            print(Fore.GREEN + f"配置已保存到 {config_path}")
        elif idx == 4:
            show_config(config)
        elif idx == 5:
            try:
                os.remove("conversion_checkpoint.pkl")
                print(Fore.GREEN + "断点文件已清除")
            except FileNotFoundError:
                print(Fore.YELLOW + "断点文件不存在")
        elif idx == 6:
            # 导出报告
            if converter is None:
                print(Fore.YELLOW + "请先运行一次转换任务。")
            else:
                converter.export_report('txt')
                converter.export_report('csv')
                converter.export_report('html')
        elif idx == 7:
            # 导出性能分析报告
            if converter is None:
                print(Fore.YELLOW + "请先运行一次转换任务。")
            else:
                converter.export_performance_report('txt')
                converter.export_performance_report('csv')
        elif idx == 8:
            # 导出智能分析报告
            if converter is None:
                print(Fore.YELLOW + "请先运行一次转换任务。")
            else:
                converter.export_smart_analysis_report('txt')
                converter.export_smart_analysis_report('csv')
                converter.export_smart_analysis_report('html')
        elif idx == 9:
            # 智能重试失败文件
            if converter is None or not hasattr(converter, 'report_details'):
                print(Fore.YELLOW + "请先运行一次转换任务。")
            else:
                # 统计失败原因
                fail_details = [d for d in converter.report_details if d['result'] in ('error','nfo_missing','delete_failed')]
                if not fail_details:
                    print(Fore.GREEN + "没有可重试的失败文件！")
                    continue
                reason_count = {}
                for d in fail_details:
                    reason = d['result']
                    reason_count[reason] = reason_count.get(reason, 0) + 1
                print(Fore.LIGHTYELLOW_EX + "失败原因分布：")
                for k,v in reason_count.items():
                    print(f"  {k}: {v} 个")
                print(Style.RESET_ALL)
                print("失败文件及修复建议：")
                for i, d in enumerate(fail_details, 1):
                    suggest = converter.analyze_error_and_suggest(d)
                    print(f"{i}. {d['file']} | {d['result']} | {d.get('error','')} | 建议: {suggest}")
                print("1. 全部重试\n2. 仅重试NFO缺失\n3. 仅重试转换错误\n4. 仅重试删除失败\n5. 自动修复可修复问题后重试")
                opt = input("请选择重试类型（回车默认全部）: ").strip()
                if opt == '2':
                    retry_list = [d for d in fail_details if d['result']=='nfo_missing']
                elif opt == '3':
                    retry_list = [d for d in fail_details if d['result']=='error']
                elif opt == '4':
                    retry_list = [d for d in fail_details if d['result']=='delete_failed']
                elif opt == '5':
                    # 自动修复可修复问题（如NFO缺失可AI补全、字段缺失可AI补全）
                    retry_list = []
                    for d in fail_details:
                        if d['result'] == 'nfo_missing' or (d['result'] == 'error' and '补全' in converter.analyze_error_and_suggest(d)):
                            retry_list.append(d)
                    print(Fore.LIGHTCYAN_EX + f"即将自动修复并重试 {len(retry_list)} 个文件..." + Style.RESET_ALL)
                else:
                    retry_list = fail_details
                print(Fore.LIGHTCYAN_EX + f"即将重试 {len(retry_list)} 个文件..." + Style.RESET_ALL)
                success, fail = 0, 0
                for d in retry_list:
                    try:
                        converter._process_video_file(d['dir'], d['file'])
                        success += 1
                    except Exception:
                        fail += 1
                print(Fore.GREEN + f"重试完成，成功: {success}，失败: {fail}")
        elif idx == 10:
            # 智能助手/语义命令
            print(Fore.LIGHTCYAN_EX + "请输入你的需求（如：只处理2020年以后的mp4，线程数8，图片压缩到100KB等）：" + Style.RESET_ALL)
            cmd = input(Fore.CYAN + ">> " + Style.RESET_ALL).strip()
            if not cmd:
                print(Fore.YELLOW + "未输入任何内容，已返回菜单。")
                continue
            rec = parse_semantic_command(cmd, config)
            print(f"\n{Fore.LIGHTGREEN_EX}解析结果推荐配置如下：{Style.RESET_ALL}")
            for field in rec.__dataclass_fields__:
                print(f"{Fore.LIGHTYELLOW_EX}{field}{Style.RESET_ALL}: {Fore.CYAN}{getattr(rec, field)}{Style.RESET_ALL}")
            accept = input(f"\n{Fore.GREEN}是否采纳推荐配置？(Y/n): {Style.RESET_ALL}").strip().lower()
            if accept in ('', 'y', 'yes'):
                config = rec
                print(Fore.GREEN + "已采纳智能助手推荐配置！")
            else:
                print(Fore.YELLOW + "未采纳，配置未变更。")
        elif idx == -1:
            print(Fore.YELLOW + "已返回上一级菜单。")

if __name__ == '__main__':
    main() 