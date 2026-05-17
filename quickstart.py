#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA 转换器 - 快速启动菜单

提供友好的交互式菜单选择
"""

import sys
import os
import subprocess
from pathlib import Path


def clear_screen():
    """清除屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """打印标题"""
    header = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║    NFO  → VSMETA 转换器  v2.0.1                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(header)


def print_menu():
    """打印主菜单"""
    menu = """
请选择操作:

[1] 运行主程序 (命令行界面)
[2] 启动 Web UI
[3] 插件系统测试
[4] 运行单元测试
[5] 创建新插件
[6] 查看帮助
[7] 打开项目文档
[0] 退出
"""
    print(menu)


def run_main_program():
    """运行主程序"""
    print("\n🚀 启动主程序...")
    subprocess.run([sys.executable, "nfo_to_vsmeta_converter_complete.py", "-h"])
    input("\n按 Enter 继续...")


def run_web_ui():
    """运行 Web UI"""
    print("\n🌐 启动 Web UI...")
    print("访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止")
    print("-" * 50)
    try:
        subprocess.run([sys.executable, "web_ui.py"])
    except KeyboardInterrupt:
        print("\n\nWeb UI 已停止")


def run_plugin_test():
    """运行插件系统测试"""
    print("\n🔌 运行插件系统测试...")
    subprocess.run([sys.executable, "test_plugins.py"])
    input("\n按 Enter 继续...")


def run_unit_tests():
    """运行单元测试"""
    print("\n🧪 运行单元测试...")
    try:
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])
    except FileNotFoundError:
        print("⚠️  pytest 未安装，尝试不使用 pytest")
        print("   运行基本测试...")
    input("\n按 Enter 继续...")


def create_new_plugin():
    """创建新插件"""
    print("\n🔧 创建新插件...")
    print("请输入插件信息:")

    plugin_name = input("插件名称 (例如: my_plugin): ").strip()
    if not plugin_name:
        print("❌ 插件名称不能为空")
        input("\n按 Enter 继续...")
        return

    print("\n插件类型:")
    print("  [1] NFOParserPlugin    - NFO 解析器")
    print("  [2] VSMETAGeneratorPlugin - VSMETA 生成器")
    print("  [3] MetadataEnhancerPlugin - 元数据增强器")
    print("  [4] FileFilterPlugin  - 文件过滤器")
    print("  [5] LifecyclePlugin    - 生命周期插件")

    type_choice = input("\n选择插件类型 (1-5): ").strip()
    type_map = {
        "1": "parser",
        "2": "generator",
        "3": "enhancer",
        "4": "filter",
        "5": "lifecycle"
    }

    plugin_type = type_map.get(type_choice, "enhancer")

    author = input("作者名称: ").strip() or "Anonymous"
    description = input("插件描述: ").strip() or f"{plugin_name} plugin"

    args = [
        sys.executable,
        "nfo_to_vsmeta_converter_complete.py",
        "--create-plugin", plugin_name,
        "--plugin-type", plugin_type,
        "--plugin-author", author,
        "--plugin-description", description
    ]

    print(f"\n正在创建插件: {plugin_name} (类型: {plugin_type})")
    subprocess.run(args)
    input("\n按 Enter 继续...")


def show_help():
    """显示帮助"""
    clear_screen()
    print_header()
    help_text = """
📚 使用帮助

主程序:
  python nfo_to_vsmeta_converter_complete.py [选项]

常用命令:
  -h, --help              显示帮助
  -d, --directory PATH    指定处理目录
  --workers N             设置工作线程数
  --overwrite             覆盖已有文件
  --dry-run               预演模式

Web UI:
  python web_ui.py
  访问 http://localhost:5000

创建插件:
  python nfo_to_vsmeta_converter_complete.py --create-plugin NAME --plugin-type TYPE

运行测试:
  python -m pytest tests/ -v

更多文档:
  查看 README.md 或访问 docs/ 目录
"""
    print(help_text)
    input("\n按 Enter 继续...")


def open_documentation():
    """打开项目文档"""
    print("\n📖 打开项目文档...")
    readme_path = Path("README.md")
    if readme_path.exists():
        print("找到 README.md，尝试打开...")
        try:
            if os.name == 'nt':
                os.startfile(str(readme_path))
            else:
                subprocess.run(['xdg-open', str(readme_path)])
        except Exception:
            print(f"请手动打开文件: {readme_path.absolute()}")
    else:
        print("未找到 README.md")
    input("\n按 Enter 继续...")


def main():
    """主函数"""
    while True:
        try:
            clear_screen()
            print_header()
            print_menu()

            choice = input("请选择 (0-7): ").strip()

            if choice == "0":
                print("\n👋 再见!")
                break
            elif choice == "1":
                run_main_program()
            elif choice == "2":
                run_web_ui()
            elif choice == "3":
                run_plugin_test()
            elif choice == "4":
                run_unit_tests()
            elif choice == "5":
                create_new_plugin()
            elif choice == "6":
                show_help()
            elif choice == "7":
                open_documentation()
            else:
                print("\n❌ 无效的选择，请重试")
                input("\n按 Enter 继续...")
        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            input("\n按 Enter 继续...")


if __name__ == "__main__":
    main()
