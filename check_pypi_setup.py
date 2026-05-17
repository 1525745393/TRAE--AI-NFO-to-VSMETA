#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyPI 配置验证和准备脚本
检查 PyPI 发布配置是否完整
"""

import sys
import os
from pathlib import Path


def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🔧 PyPI 配置检查和验证工具                                     ║
║   NFO to VSMETA Converter - v2.0.1                               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_pyproject_toml():
    """检查 pyproject.toml"""
    print("\n" + "="*60)
    print("📁 1. 检查 pyproject.toml")
    print("="*60)
    
    path = Path("pyproject.toml")
    
    if not path.exists():
        print("❌ pyproject.toml 不存在")
        return False
    
    print("✅ pyproject.toml 存在")
    
    content = path.read_text()
    
    checks = [
        ("项目名称", 'name = "nfo-to-vsmeta"'),
        ("版本号", 'version = "2.0.1"'),
        ("描述", 'description ='),
        ("作者", 'authors ='),
        ("URLs", '[project.urls]'),
        ("依赖", '[project.optional-dependencies]'),
        ("脚本", '[project.scripts]'),
        ("Setuptools", '[tool.setuptools]'),
        ("Pytest", '[tool.pytest.ini_options]'),
    ]
    
    all_passed = True
    for name, check in checks:
        if check in content:
            print(f"  ✅ {name}: 找到")
        else:
            print(f"  ⚠️  {name}: 未找到")
            all_passed = False
    
    return all_passed


def check_manifest():
    """检查 MANIFEST.in"""
    print("\n" + "="*60)
    print("📁 2. 检查 MANIFEST.in")
    print("="*60)
    
    path = Path("MANIFEST.in")
    
    if not path.exists():
        print("❌ MANIFEST.in 不存在")
        return False
    
    print("✅ MANIFEST.in 存在")
    
    content = path.read_text()
    checks = [
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "requirements.txt",
    ]
    
    all_passed = True
    for check in checks:
        if check in content:
            print(f"  ✅ 包含 {check}")
        else:
            print(f"  ⚠️  {check} 未在 MANIFEST.in 中明确声明")
    
    return all_passed


def check_requirements():
    """检查 requirements.txt"""
    print("\n" + "="*60)
    print("📦 3. 检查 requirements.txt")
    print("="*60)
    
    path = Path("requirements.txt")
    
    if not path.exists():
        print("❌ requirements.txt 不存在")
        return False
    
    print("✅ requirements.txt 存在")
    
    content = path.read_text()
    packages = [
        "Pillow",
        "tqdm",
        "colorama",
        "readchar",
        "watchdog",
        "Flask",
        "black",
        "mypy",
        "pytest",
        "flake8",
    ]
    
    print(f"  文件行数: {len(content.splitlines())}")
    
    found_count = 0
    for package in packages:
        if package in content:
            found_count += 1
            print(f"  ✅ {package}: 找到")
        else:
            print(f"  ℹ️ {package}: 未找到（可能在可选依赖中）")
    
    print(f"  找到 {found_count}/{len(packages)} 个常见依赖")
    
    return True


def check_pypirc():
    """检查 .pypirc 配置"""
    print("\n" + "="*60)
    print("🔐 4. 检查 .pypirc 配置")
    print("="*60)
    
    home = Path.home()
    pypirc_path = home / ".pypirc"
    
    if not pypirc_path.exists():
        print("❌ .pypirc 不存在（在用户主目录中）")
        print(f"   预期位置: {pypirc_path}")
        print("\n   请参考 PYPI_SETUP.md 创建该文件")
        return False
    
    print("✅ .pypirc 存在")
    
    content = pypirc_path.read_text()
    
    sections = [
        "[distutils]",
        "[pypi]",
        "[testpypi]",
    ]
    
    for section in sections:
        if section in content:
            print(f"  ✅ {section}: 存在")
        else:
            print(f"  ❌ {section}: 缺失")
    
    # 检查是否使用 Token 认证
    if "username = __token__" in content:
        print("  ✅ 使用 Token 认证（推荐）")
    else:
        print("  ⚠️  未检测到 Token 认证（建议使用 Token）")
    
    # 检查权限（Linux/Mac 专属）
    if sys.platform != "win32":
        try:
            mode = oct(pypirc_path.stat().st_mode)[-3:]
            if mode == "600":
                print("  ✅ 文件权限正确 (0600)")
            else:
                print(f"  ⚠️  文件权限: {mode}（建议 0600）")
                print(f"     修复: chmod 600 {pypirc_path}")
        except Exception as e:
            print(f"  ℹ️ 无法检查权限: {e}")
    
    return True


def check_build_tools():
    """检查打包工具是否已安装"""
    print("\n" + "="*60)
    print("🛠️  5. 检查打包工具")
    print("="*60)
    
    tools = [
        ("build", "构建包"),
        ("twine", "上传包"),
        ("wheel", "Wheel 格式支持"),
    ]
    
    all_passed = True
    for tool, desc in tools:
        try:
            __import__(tool)
            print(f"  ✅ {tool}: 已安装（{desc}）")
        except ImportError:
            print(f"  ❌ {tool}: 未安装（{desc}）")
            all_passed = False
    
    return all_passed


def check_project_files():
    """检查项目关键文件是否存在"""
    print("\n" + "="*60)
    print("📚 6. 检查项目关键文件")
    print("="*60)
    
    files = [
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "nfo_to_vsmeta_converter_complete.py",
        "web_ui.py",
        "release.py",
        "requirements.txt",
        "pyproject.toml",
        "MANIFEST.in",
    ]
    
    all_passed = True
    for file in files:
        path = Path(file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {file}: 存在（{size} bytes）")
        else:
            print(f"  ❌ {file}: 缺失！")
            all_passed = False
    
    return all_passed


def print_summary(results):
    """打印总结"""
    print("\n" + "="*60)
    print("📊 检查总结")
    print("="*60)
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\n总检查项: {total}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    if failed == 0:
        print("\n" + "🎉"*15)
        print("  🎊 所有检查通过！准备发布！🎊")
        print("🎉"*15 + "\n")
        print("下一步操作:")
        print("  1. 运行: python release.py full")
        print("  2. 测试 Test PyPI: python release.py testpypi")
        print("  3. 正式发布: python release.py pypi")
    else:
        print("\n⚠️  有一些问题需要解决，请查看上面的检查结果")
        print("\n参考文档:")
        print("  - PYPI_SETUP.md - PyPI 账户创建指南")
        print("  - RELEASE_GUIDE.md - 完整发布指南")


def main():
    """主函数"""
    print_banner()
    
    results = []
    
    results.append(check_pyproject_toml())
    results.append(check_manifest())
    results.append(check_requirements())
    results.append(check_pypirc())
    results.append(check_build_tools())
    results.append(check_project_files())
    
    print_summary(results)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
