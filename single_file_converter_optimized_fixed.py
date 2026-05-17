"""
NFO to VSMETA 转换器 - 完全优化版
支持：多线程、断点续传、智能重试、AI补全
"""

import argparse
import copy
import itertools
import logging
import os
import re
import time

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    # colorama 未安装时的回退
    class _Fore:
        CYAN = GREEN = YELLOW = RED = LIGHTMAGENTA_EX = ''
        LIGHTBLACK_EX = LIGHTYELLOW_EX = LIGHTCYAN_EX = LIGHTGREEN_EX = ''
        BRIGHT = ''
    class _Style:
        RESET_ALL = BRIGHT = ''
    Fore = _Fore()
    Style = _Style()

try:
    import readchar
    HAS_READCHAR = True
except ImportError:
    HAS_READCHAR = False

logger = logging.getLogger(__name__)


# ============================================================================
# 以下类和函数由其他模块提供，此处仅做占位声明
# 实际使用时请从对应模块导入，例如：
#   from your_config_module import Config, interactive_config_with_validation, recommend_config
#   from your_converter_module import NFOToVSMETAConverter
# ============================================================================

class Config:
    """配置类占位 — 请替换为实际实现"""
    def __init__(self, **kwargs):
        self.directory = kwargs.get('directory', '.')
        self.file_include_patterns = kwargs.get('file_include_patterns', None)
        self.file_regex = kwargs.get('file_regex', None)
        self.max_image_size_kb = kwargs.get('max_image_size_kb', 200)
        self.image_compression_ratio = kwargs.get('image_compression_ratio', 0.8)
        self.max_workers = kwargs.get('max_workers', 4)
        self.retry_attempts = kwargs.get('retry_attempts', 3)
        self.retry_delay = kwargs.get('retry_delay', 1.0)
        self.log_level = kwargs.get('log_level', 'INFO')
        self.process_mode = kwargs.get('process_mode', 'thread')
        self.overwrite_existing = kwargs.get('overwrite_existing', False)
        self.delete_existing_vsmeta = kwargs.get('delete_existing_vsmeta', False)
        self.enable_backup = kwargs.get('enable_backup', True)
        self.min_size = kwargs.get('min_size', 0)

    @classmethod
    def from_file(cls, path):
        """从 JSON 文件加载配置"""
        import json
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        except FileNotFoundError:
            logger.warning(f"配置文件 {path} 不存在，使用默认配置")
            return cls()

    def save_to_file(self, path):
        """保存配置到 JSON 文件"""
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, indent=2, ensure_ascii=False)


class NFOToVSMETAConverter:
    """转换器类占位 — 请替换为实际实现"""
    def __init__(self, config):
        self.config = config
        self.stats = type('Stats', (), {'total_files': 0})()
        self.report_details = []

    def process_with_checkpoint(self):
        """带断点续传的处理流程（占位）"""
        print(f"{Fore.YELLOW}转换器未完整实现，请补充 NFOToVSMETAConverter 类{Style.RESET_ALL}")

    def export_report(self, fmt):
        print(f"{Fore.YELLOW}export_report({fmt}) — 占位方法{Style.RESET_ALL}")

    def export_performance_report(self, fmt='txt'):
        print(f"{Fore.YELLOW}export_performance_report({fmt}) — 占位方法{Style.RESET_ALL}")

    def export_smart_analysis_report(self, fmt='txt'):
        print(f"{Fore.YELLOW}export_smart_analysis_report({fmt}) — 占位方法{Style.RESET_ALL}")

    def analyze_error_and_suggest(self, detail):
        return "建议检查文件是否存在且格式正确"


def interactive_config_with_validation():
    """交互式配置向导（占位）"""
    print(f"{Fore.YELLOW}interactive_config_with_validation — 占位函数{Style.RESET_ALL}")
    return Config()


def recommend_config():
    """智能推荐配置（占位）"""
    print(f"{Fore.YELLOW}recommend_config — 占位函数{Style.RESET_ALL}")
    return Config()


# ============================================================================
# 工具函数
# ============================================================================

def spinner(msg, duration=2):
    """显示旋转加载动画"""
    for c in itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']):
        print(f"\r{Fore.LIGHTMAGENTA_EX}{msg} {c}{Style.RESET_ALL}", end='', flush=True)
        time.sleep(0.1)
        duration -= 0.1
        if duration <= 0:
            break
    print("\r", end='')


def show_menu_with_arrows(options, title="NFO to VSMETA 转换器 - 完全优化版"):
    """支持上下键选择的菜单，返回选中项索引。

    返回值:
        0 ~ len(options)-1: 选中的选项索引
        -1: 返回上一级（按 b/B）
        len(options): 退出（按 q/Q）
    """
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
        except ValueError:
            pass
        return len(options)

    # 有 readchar 时的交互式菜单
    idx = 0
    while True:
        # 清屏并渲染菜单
        print("\033[2J\033[H")
        print(f"\n{Fore.CYAN}{'🟢' * 8} {Style.BRIGHT}{title}{'🟢' * 8}{Style.RESET_ALL}")
        for i, opt in enumerate(options):
            prefix = '👉' if i == idx else '  '
            color = Fore.GREEN if i == idx else Fore.YELLOW
            print(f"{color}{prefix} {i + 1}. {opt}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLACK_EX}{'-' * 40}{Style.RESET_ALL}")
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
            return len(options)
        elif key.isdigit():
            num = int(key)
            if 1 <= num <= len(options):
                return num - 1


def show_config(config):
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
    for field in config.__dataclass_fields__ if hasattr(config, '__dataclass_fields__') else config.__dict__:
        print(f"{field}: {getattr(config, field)}")
    print()


def parse_semantic_command(cmd, base_config=None):
    """解析自然语言/语义化命令，返回推荐 Config。

    支持的命令示例:
        - 设置目录 "/path/to/movies" 和 "/path/to/series"
        - 使用8个线程处理，图片大小限制200KB
        - 过滤文件名 "*.mkv" 或正则 ".*1080p.*"
        - 只处理2020年以后的mp4
        - 只处理大于2GB的文件
        - 图片压缩到100KB，压缩比例0.7
    """
    config = copy.deepcopy(base_config) if base_config else Config()
    cmd_lower = cmd.lower()

    # --- 目录设置 ---
    if "目录" in cmd or "path" in cmd_lower:
        paths = re.findall(r'"([^"]+)"', cmd)
        if paths:
            config.directory = paths if len(paths) > 1 else paths[0]

    # --- 文件格式过滤 ---
    ext_matches = re.findall(r'(mp4|mkv|avi|ts|wmv|rmvb)', cmd_lower)
    if ext_matches:
        config.file_include_patterns = [f'*.{ext}' for ext in ext_matches]

    # --- 文件大小过滤 ---
    size_match = re.search(r'大于(\d+)(g|gb|m|mb)', cmd)
    if size_match:
        size_val = int(size_match.group(1))
        unit = size_match.group(2)
        if unit.startswith('g'):
            config.min_size = size_val * 1024 * 1024 * 1024
        else:
            config.min_size = size_val * 1024 * 1024

    # --- 年份过滤 ---
    year_match = re.search(r'(\d{4})年以?后', cmd)
    if year_match:
        year = int(year_match.group(1))
        config.file_regex = '|'.join(str(y) for y in range(year + 1, year + 10))

    # --- 图片大小限制 ---
    img_size_match = re.search(r'(图片|海报|压缩)[^\d]*(\d+)\s*[kK][bB]', cmd)
    if img_size_match:
        config.max_image_size_kb = int(img_size_match.group(2))

    # --- 压缩比例 ---
    ratio_match = re.search(r'(压缩比例|压缩比)[^\d]*(0\.\d+|1\.0|1)', cmd)
    if ratio_match:
        config.image_compression_ratio = float(ratio_match.group(2))

    # --- 线程数 ---
    thread_match = re.search(r'(线程数|多线程|thread)[^\d]*(\d+)', cmd_lower)
    if thread_match:
        config.max_workers = min(16, max(1, int(thread_match.group(2))))

    # --- 重试次数 ---
    retry_match = re.search(r'重试(\d+)次', cmd)
    if retry_match:
        config.retry_attempts = int(retry_match.group(1))

    # --- 日志级别 ---
    if "日志" in cmd:
        levels = {"debug": "DEBUG", "info": "INFO", "warning": "WARNING", "error": "ERROR"}
        for k, v in levels.items():
            if k in cmd_lower:
                config.log_level = v
                break

    # --- 处理模式 ---
    if "进程" in cmd:
        config.process_mode = "process"
    elif "线程" in cmd:
        config.process_mode = "thread"

    # --- 文件过滤（通配符或正则） ---
    if "过滤" in cmd:
        patterns = re.findall(r'"([^"]+)"', cmd)
        if patterns:
            if '*' in patterns[0] or '?' in patterns[0]:
                config.file_include_patterns = patterns
            else:
                config.file_regex = patterns[0]

    # --- 关键词过滤（兜底） ---
    keyword_matches = re.findall(r'只处理.*?([\u4e00-\u9fa5a-zA-Z0-9]+)', cmd)
    if keyword_matches and not config.file_regex:
        config.file_regex = '|'.join(keyword_matches)

    return config


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
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

        # 退出
        if idx == len(menu_options):
            print(f"{Fore.GREEN}再见！{Style.RESET_ALL}")
            break
        # 返回上一级（当前为顶级菜单，等同于退出）
        elif idx == -1:
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
            config_path = input(f"{Fore.CYAN}>> {Style.RESET_ALL}请输入配置文件路径 (默认: config.json): ").strip()
            if not config_path:
                config_path = 'config.json'
            config = Config.from_file(config_path)
            converter = NFOToVSMETAConverter(config)
            converter.process_with_checkpoint()

        elif idx == 3:
            # 保存当前配置到文件
            config_path = input(f"{Fore.CYAN}>> {Style.RESET_ALL}请输入保存路径 (默认: config.json): ").strip()
            if not config_path:
                config_path = 'config.json'
            config.save_to_file(config_path)
            print(f"{Fore.GREEN}配置已保存到 {config_path}{Style.RESET_ALL}")

        elif idx == 4:
            # 显示当前配置
            show_config(config)

        elif idx == 5:
            # 清除断点文件
            try:
                os.remove("conversion_checkpoint.pkl")
                print(f"{Fore.GREEN}断点文件已清除{Style.RESET_ALL}")
            except FileNotFoundError:
                print(f"{Fore.YELLOW}断点文件不存在{Style.RESET_ALL}")

        elif idx == 6:
            # 导出处理报告
            if converter is None:
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                converter.export_report('txt')
                converter.export_report('csv')
                converter.export_report('html')

        elif idx == 7:
            # 导出性能分析报告
            if converter is None:
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                converter.export_performance_report('txt')
                converter.export_performance_report('csv')

        elif idx == 8:
            # 导出智能分析报告
            if converter is None:
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                converter.export_smart_analysis_report('txt')
                converter.export_smart_analysis_report('csv')
                converter.export_smart_analysis_report('html')

        elif idx == 9:
            # 智能重试失败文件
            if converter is None or not hasattr(converter, 'report_details'):
                print(f"{Fore.YELLOW}请先运行一次转换任务。{Style.RESET_ALL}")
            else:
                fail_details = [
                    d for d in converter.report_details
                    if d['result'] in ('error', 'nfo_missing', 'delete_failed')
                ]
                if not fail_details:
                    print(f"{Fore.GREEN}没有可重试的失败文件！{Style.RESET_ALL}")
                    input("\n按回车键继续...")
                    continue

                # 统计失败原因
                reason_count = {}
                for d in fail_details:
                    reason = d['result']
                    reason_count[reason] = reason_count.get(reason, 0) + 1

                print(f"{Fore.LIGHTYELLOW_EX}失败原因分布：{Style.RESET_ALL}")
                for k, v in reason_count.items():
                    print(f"  {k}: {v} 个")
                print()

                print("失败文件及修复建议：")
                for i, d in enumerate(fail_details, 1):
                    suggest = converter.analyze_error_and_suggest(d)
                    print(f"{i}. {d['file']} | {d['result']} | {d.get('error', '')} | 建议: {suggest}")

                print("\n1. 全部重试")
                print("2. 仅重试NFO缺失")
                print("3. 仅重试转换错误")
                print("4. 仅重试删除失败")
                print("5. 自动修复可修复问题后重试")
                opt = input("请选择重试类型（回车默认全部）: ").strip()

                if opt == '2':
                    retry_list = [d for d in fail_details if d['result'] == 'nfo_missing']
                elif opt == '3':
                    retry_list = [d for d in fail_details if d['result'] == 'error']
                elif opt == '4':
                    retry_list = [d for d in fail_details if d['result'] == 'delete_failed']
                elif opt == '5':
                    retry_list = []
                    for d in fail_details:
                        if d['result'] == 'nfo_missing' or (
                            d['result'] == 'error'
                            and '补全' in converter.analyze_error_and_suggest(d)
                        ):
                            retry_list.append(d)
                    print(f"{Fore.LIGHTCYAN_EX}即将自动修复并重试 {len(retry_list)} 个文件...{Style.RESET_ALL}")
                else:
                    retry_list = fail_details

                print(f"{Fore.LIGHTCYAN_EX}即将重试 {len(retry_list)} 个文件...{Style.RESET_ALL}")
                success, fail = 0, 0
                for d in retry_list:
                    try:
                        converter._process_video_file(d['dir'], d['file'])
                        success += 1
                    except Exception:
                        fail += 1
                print(f"{Fore.GREEN}重试完成，成功: {success}，失败: {fail}{Style.RESET_ALL}")

        elif idx == 10:
            # 智能助手/语义命令
            print(f"{Fore.LIGHTCYAN_EX}请输入你的需求（如：只处理2020年以后的mp4，线程数8，图片压缩到100KB等）：{Style.RESET_ALL}")
            cmd = input(f"{Fore.CYAN}>> {Style.RESET_ALL}").strip()
            if not cmd:
                print(f"{Fore.YELLOW}未输入任何内容，已返回菜单。{Style.RESET_ALL}")
                input("\n按回车键继续...")
                continue

            rec = parse_semantic_command(cmd, config)
            print(f"\n{Fore.LIGHTGREEN_EX}解析结果推荐配置如下：{Style.RESET_ALL}")
            for field in rec.__dict__:
                print(f"{Fore.LIGHTYELLOW_EX}{field}{Style.RESET_ALL}: {Fore.CYAN}{getattr(rec, field)}{Style.RESET_ALL}")

            accept = input(f"\n{Fore.GREEN}是否采纳推荐配置？(Y/n): {Style.RESET_ALL}").strip().lower()
            if accept in ('', 'y', 'yes'):
                config = rec
                print(f"{Fore.GREEN}已采纳智能助手推荐配置！{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}未采纳，配置未变更。{Style.RESET_ALL}")

        input("\n按回车键继续...")


if __name__ == '__main__':
    main()
