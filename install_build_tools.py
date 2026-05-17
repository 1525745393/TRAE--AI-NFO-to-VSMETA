#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速安装 PyPI 打包工具
一键安装 build、twine、wheel
"""

import sys
import subprocess
import shlex


def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   📦 PyPI 打包工具 - 快速安装                                   ║
║   NFO to VSMETA Converter - v2.0.1                               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_cmd(cmd):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False


def install_package(package):
    """安装单个包"""
    print(f"正在安装 {package}...")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package]
    success = run_cmd(cmd)
    if success:
        print(f"✅ {package} 安装成功")
    return success


def check_installed(package):
    """检查包是否已安装"""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def main():
    """主函数"""
    print_banner()
    
    print("\n" + "="*60)
    print("需要安装的工具:")
    print("  1. build - 构建工具")
    print("  2. twine - 上传工具")
    print("  3. wheel - Wheel 格式支持")
    print("="*60)
    
    # 检查已安装的包
    print("\n检查已安装...")
    packages = ["build", "twine", "wheel"]
    installed = [pkg for pkg in packages if check_installed(pkg)]
    
    if installed:
        print(f"✅ 已安装: {', '.join(installed)}")
    
    to_install = [pkg for pkg in packages if not check_installed(pkg)]
    
    if not to_install:
        print("\n🎉 所有工具已安装完成！")
        print("\n下一步:")
        print("  1. 创建 PyPI 账户（参考 PYPI_SETUP.md）")
        print("  2. 运行: python check_pypi_setup.py")
        print("  3. 运行: python release.py full")
        return 0
    
    # 安装缺失的包
    print(f"\n📦 正在安装: {', '.join(to_install)}")
    success = True
    
    for pkg in to_install:
        if not install_package(pkg):
            success = False
    
    # 再次检查
    print("\n" + "="*60)
    print("📊 安装结果:")
    final_check = [pkg for pkg in packages if check_installed(pkg)]
    
    if len(final_check) == 3:
        print("🎉 所有工具安装成功！")
        print("\n✅ build 已安装")
        print("✅ twine 已安装")
        print("✅ wheel 已安装")
    else:
        print(f"⚠️  安装了 {len(final_check)}/3 个工具")
        print(f"   已安装: {', '.join(final_check)}")
    
    print("\n下一步:")
    print("  1. 创建 PyPI 账户（参考 PYPI_SETUP.md）")
    print("  2. 运行: python check_pypi_setup.py")
    print("  3. 运行: python release.py full")
    
    return 0 if len(final_check) == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
