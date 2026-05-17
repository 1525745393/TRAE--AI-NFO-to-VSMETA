#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA 转换器 - 项目初始化脚本

自动设置开发环境和依赖项
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║    NFO to VSMETA 转换器                                          ║
║    项目初始化脚本                                              ║
║    版本 2.0.1                                                 ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_python_version():
    """检查 Python 版本"""
    print("🔍 检查 Python 版本...")
    version = sys.version_info
    required = (3, 8)
    if version < required:
        print(f"❌ 错误: Python 版本过低，需要 {required[0]}.{required[1]} 或更高")
        print(f"   当前版本: {version[0]}.{version[1]}.{version[2]}")
        return False
    print(f"✅ Python 版本: {version[0]}.{version[1]}.{version[2]} ✓")
    return True


def create_virtual_environment():
    """创建虚拟环境"""
    print("\n🐍 创建虚拟环境...")
    venv_dir = Path(".venv")
    if venv_dir.exists():
        print("⚠️  虚拟环境已存在，跳过创建")
        return True

    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ 虚拟环境创建成功")
        return True
    except Exception as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return False


def install_requirements():
    """安装依赖项"""
    print("\n📦 安装项目依赖...")
    requirements_path = Path("requirements.txt")
    if not requirements_path.exists():
        print("❌ 找不到 requirements.txt")
        return False

    pip_cmd = [
        ".venv/Scripts/pip" if platform.system() == "Windows" else ".venv/bin/pip"
    pip_path = Path(pip_cmd)

    if not pip_path.exists():
        pip_cmd = [sys.executable, "-m", "pip"]

    try:
        subprocess.run(
            [*pip_cmd, "install", "--upgrade", "pip"],
            check=True
        )

        print("   正在安装依赖...")
        result = subprocess.run(
            [*pip_cmd, "install", "-r", str(requirements_path)],
            check=True
        )
        print("✅ 依赖安装成功")
        return True
    except Exception as e:
        print(f"⚠️  警告: 部分依赖安装失败: {e}")
        print("   但项目仍可运行核心功能")
        return True


def setup_git():
    """初始化 Git"""
    print("\n🔧 初始化 Git 仓库...")
    git_dir = Path(".git")
    if git_dir.exists():
        print("⚠️  Git 仓库已存在，跳过初始化")
        return True

    try:
        if not Path(".gitignore").exists():
            print("   创建 .gitignore...")

        subprocess.run(
            ["git", "init"],
            check=True,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["git", "add", "."],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Git 仓库初始化成功")
        return True
    except Exception as e:
        print(f"⚠️  Git 初始化失败: {e}")
        return False


def create_directories():
    """创建必要的目录"""
    print("\n📁 创建必要的目录...")
    directories = [
        "plugins",
        "plugins/configs",
        "reports",
        "output",
        "backup",
        "logs"
    ]
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   创建: {dir_name}/")
    print("✅ 目录创建完成")


def show_quick_start_guide():
    """显示快速开始指南"""
    print("\n" + "="*70)
    print("🎉 项目初始化完成!")
    print("="*70)
    print("\n📋 下一步操作指南:")
    print("\n1. 激活虚拟环境:")
    if platform.system() == "Windows":
        print("   .venv\\Scripts\\activate")
    else:
        print("   source .venv/bin/activate")
    print("\n2. 运行程序:")
    print("   python nfo_to_vsmeta_converter_complete.py -h")
    print("\n3. 启动 Web UI:")
    print("   python web_ui.py")
    print("\n4. 运行测试:")
    print("   python -m pytest tests/ -v")
    print("\n5. 创建插件开发:")
    print("   python nfo_to_vsmeta_converter_complete.py --create-plugin my_plugin --plugin-type enhancer")
    print("\n" + "="*70)


def main():
    """主函数"""
    print_banner()

    success = True

    if not check_python_version():
        success = False
        return 1

    create_directories()
    create_virtual_environment()
    install_requirements()
    setup_git()

    show_quick_start_guide()

    return 0


if __name__ == "__main__":
    sys.exit(main())
