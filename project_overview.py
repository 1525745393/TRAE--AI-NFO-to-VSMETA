#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA 转换器 - 项目概览

展示项目整体状态
"""

import os
from pathlib import Path


def count_lines(file_path):
    """计算文件行数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f)
    except Exception:
        return 0


def get_size(file_path):
    """获取文件大小（KB）"""
    try:
        return round(os.path.getsize(file_path) / 1024, 1)
    except Exception:
        return 0


def print_project_overview():
    """打印项目概览"""
    print("\n" + "=" * 70)
    print("📊 NFO to VSMETA 转换器 - 项目概览")
    print("=" * 70)

    project_root = Path(".")

    # 核心文件
    core_files = [
        "nfo_to_vsmeta_converter_complete.py",
        "web_ui.py",
        "single_file_converter_optimized_fixed.py",
        "test_plugins.py",
        "setup.py",
        "quickstart.py",
    ]

    total_lines = 0
    total_size = 0

    print("\n📁 核心程序文件:")
    print("-" * 40)
    for filename in core_files:
        if (project_root / filename).exists():
            lines = count_lines(filename)
            size = get_size(filename)
            total_lines += lines
            total_size += size
            print(f"  {filename:<45} {lines:>6} 行  {size:>5} KB")

    # 文档文件
    doc_files = [
        "README.md",
        "PROJECT_STATUS.md",
        "PROJECT_SUMMARY.md",
        "CHANGELOG.md",
        "DEVELOPMENT.md",
        "LICENSE",
    ]

    print("\n📚 文档文件:")
    print("-" * 40)
    for filename in doc_files:
        if (project_root / filename).exists():
            lines = count_lines(filename)
            size = get_size(filename)
            total_lines += lines
            total_size += size
            print(f"  {filename:<45} {lines:>6} 行  {size:>5} KB")

    # 配置文件
    config_files = ["requirements.txt", "pyproject.toml", ".gitignore", ".vscode/settings.json"]

    print("\n⚙️  配置文件:")
    print("-" * 40)
    for filename in config_files:
        if (project_root / filename).exists():
            lines = count_lines(filename)
            size = get_size(filename)
            total_lines += lines
            total_size += size
            print(f"  {filename:<45} {lines:>6} 行  {size:>5} KB")

    # 测试目录
    tests_dir = project_root / "tests"
    test_count = 0
    test_lines = 0
    test_size = 0
    if tests_dir.exists():
        test_files = list(tests_dir.rglob("*.py"))
        test_count = len(test_files)
        for test_file in test_files:
            lines = count_lines(test_file)
            size = get_size(test_file)
            test_lines += lines
            test_size += size
            total_lines += lines
            total_size += size

    print(f"\n🧪 测试目录: {test_count} 个 Python 文件")
    print("-" * 40)
    if test_count > 0:
        print(f"  测试代码: {test_lines} 行  {test_size} KB")

    # 插件目录
    plugins_dir = project_root / "plugins"
    plugin_count = 0
    plugin_lines = 0
    plugin_size = 0
    if plugins_dir.exists():
        plugin_files = list(plugins_dir.rglob("*.py"))
        plugin_count = len(plugin_files)
        for plugin_file in plugin_files:
            lines = count_lines(plugin_file)
            size = get_size(plugin_file)
            plugin_lines += lines
            plugin_size += size
            total_lines += lines
            total_size += size

    print(f"\n🔌 插件目录: {plugin_count} 个 Python 文件")
    print("-" * 40)
    if plugin_count > 0:
        print(f"  插件代码: {plugin_lines} 行  {plugin_size} KB")

    # 文档目录
    docs_dir = project_root / "docs"
    docs_count = 0
    docs_lines = 0
    docs_size = 0
    if docs_dir.exists():
        doc_files = list(docs_dir.rglob("*.md"))
        docs_count = len(doc_files)
        for doc_file in doc_files:
            lines = count_lines(doc_file)
            size = get_size(doc_file)
            docs_lines += lines
            docs_size += size
            total_lines += lines
            total_size += size

    print(f"\n📖 设计文档: {docs_count} 个 Markdown 文件")
    print("-" * 40)
    if docs_count > 0:
        print(f"  文档内容: {docs_lines} 行  {docs_size} KB")

    # 汇总
    print("\n" + "=" * 70)
    print("📊 项目汇总")
    print("=" * 70)
    print(f"  总代码行数:  {total_lines:,} 行")
    print(f"  总文件大小:  {total_size:.1f} KB ({total_size/1024:.1f} MB)")

    # 状态检查
    print("\n✅ 项目状态检查:")
    print("-" * 40)

    checks = [
        ("README.md", "项目主文档"),
        ("PROJECT_STATUS.md", "项目状态报告"),
        ("PROJECT_SUMMARY.md", "项目总结文档"),
        ("CHANGELOG.md", "更新日志"),
        ("DEVELOPMENT.md", "开发指南"),
        ("LICENSE", "许可证"),
        ("requirements.txt", "依赖清单"),
        ("pyproject.toml", "项目配置"),
        (".gitignore", "Git 忽略规则"),
        ("tests/", "测试目录"),
        ("plugins/", "插件目录"),
        ("docs/", "文档目录"),
        (".vscode/", "编辑器配置"),
    ]

    all_good = True
    for path, desc in checks:
        check_path = project_root / path
        if check_path.exists():
            status = "✅"
        else:
            status = "❌"
            all_good = False
        print(f"  {status} {path:<30} - {desc}")

    print("\n" + "=" * 70)
    if all_good:
        print("🎉 项目准备就绪，可以开始使用！")
    else:
        print("⚠️  部分文件缺失，请检查项目结构")
    print("=" * 70)

    # 快速启动命令
    print("\n" + "🚀 快速启动命令:")
    print("-" * 40)
    print("  python setup.py                          # 初始化项目")
    print("  python quickstart.py                      # 快速启动菜单")
    print("  python nfo_to_vsmeta_converter_complete.py -h # 查看帮助")
    print("  python web_ui.py                          # 启动 Web UI")
    print("  python -m pytest tests/ -v                # 运行测试")


if __name__ == "__main__":
    print_project_overview()
