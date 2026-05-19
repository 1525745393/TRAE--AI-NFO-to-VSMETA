#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFO to VSMETA 转换器 - 发布脚本

自动化打包、测试和发布流程
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║    NFO to VSMETA 转换器                                          ║
║    发布脚本 v2.0.1                                             ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_command(cmd, description, check=True):
    """运行命令并打印结果"""
    print(f"\n{'='*70}")
    print(f"📦 {description}")
    print(f"{'='*70}")
    print(f"命令: {cmd}\n")

    try:
        import shlex

        if isinstance(cmd, str):
            cmd_list = shlex.split(cmd)
        else:
            cmd_list = cmd
        result = subprocess.run(cmd_list, shell=False, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def clean_build_dirs():
    """清理构建目录"""
    print("\n🧹 清理构建目录...")

    dirs_to_remove = [
        "build",
        "dist",
        "*.egg-info",
        ".pytest_cache",
        "__pycache__",
        "**/__pycache__",
        ".coverage",
        "htmlcov",
        ".mypy_cache",
    ]

    for pattern in dirs_to_remove:
        if "*" in pattern:
            import glob

            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    print(f"  删除目录: {path}")
                    shutil.rmtree(path, ignore_errors=True)
        else:
            if os.path.isdir(pattern):
                print(f"  删除目录: {pattern}")
                shutil.rmtree(pattern, ignore_errors=True)


def run_tests():
    """运行测试"""
    print("\n🧪 运行测试...")

    if not run_command(f"{sys.executable} -m pytest tests/ -v", "单元测试", check=False):
        print("⚠️  测试失败，但继续发布流程...")
        return False
    return True


def check_code_quality():
    """检查代码质量"""
    print("\n🔍 检查代码质量...")

    checks = [("flake8", "代码检查"), ("mypy", "类型检查")]

    all_passed = True
    import shlex

    for tool, name in checks:
        try:
            cmd_list = shlex.split(
                f"{sys.executable} -m {tool} nfo_to_vsmeta_converter_complete.py"
            )
            result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {name}通过")
            else:
                print(f"⚠️  {name}发现问题")
                print(result.stdout)
                all_passed = False
        except Exception:
            print(f"⚠️  {name}工具未安装，跳过")
            all_passed = False

    return all_passed


def build_package():
    """构建包"""
    print("\n📦 构建发布包...")

    if not run_command(f"{sys.executable} -m build", "构建包", check=False):
        print("❌ 构建失败")
        return False

    print("\n✅ 包构建成功！")
    return True


def show_build_artifacts():
    """显示构建产物"""
    print("\n📁 构建产物:")

    dist_dir = Path("dist")
    if dist_dir.exists():
        files = list(dist_dir.iterdir())
        if files:
            for f in files:
                size = f.stat().st_size / 1024
                print(f"  📄 {f.name} ({size:.1f} KB)")
        else:
            print("  ⚠️  dist/ 目录为空")
    else:
        print("  ⚠️  dist/ 目录不存在")


def upload_to_pypi(test=False):
    """上传到 PyPI"""
    cmd = f"{sys.executable} -m twine upload dist/*"
    if test:
        cmd = f"{sys.executable} -m twine upload --repository testpypi dist/*"

    print(f"\n{'='*70}")
    print(f"📤 上传到 {'Test PyPI' if test else 'PyPI'}")
    print(f"{'='*70}")

    confirm = input(f"确认上传到 {'Test ' if test else ''}PyPI? (y/N): ").strip().lower()
    if confirm != "y":
        print("取消上传")
        return False

    return run_command(cmd, "上传到 PyPI", check=False)


def create_git_tag():
    """创建 Git 标签"""
    print("\n🏷️  创建 Git 标签...")

    version = "2.0.1"
    tag_name = f"v{version}"

    if not os.path.exists(".git"):
        print("⚠️  不是 Git 仓库，跳过")
        return False

    confirm = input(f"确认创建标签 {tag_name}? (y/N): ").strip().lower()
    if confirm != "y":
        print("取消创建标签")
        return False

    commands = [
        "git add .",
        f'git commit -m "Release {tag_name}"',
        f"git tag -a {tag_name} -m 'Release version {tag_name}'",
        "git push",
        f"git push origin {tag_name}",
    ]

    for cmd in commands:
        if not run_command(cmd, cmd.split()[0], check=False):
            print(f"⚠️  Git 命令失败: {cmd}")
            return False

    return True


def print_release_checklist():
    """打印发布检查清单"""
    print("\n" + "=" * 70)
    print("📋 发布前检查清单")
    print("=" * 70)

    checklist = [
        "✅ 项目代码完成",
        "✅ 所有测试通过",
        "✅ 代码质量检查通过",
        "✅ 文档完整",
        "✅ 版本号已更新",
        "✅ CHANGELOG.md 已更新",
        "✅ Git 仓库已初始化",
        "✅ PyPI 账户已创建",
        "✅ 构建产物检查",
        "✅ 上传到 Test PyPI",
        "✅ 测试安装",
        "✅ 正式发布",
        "✅ 创建 Git 标签",
        "✅ 发布公告",
    ]

    for item in checklist:
        print(f"  {item}")

    print("\n" + "=" * 70)


def main():
    """主函数"""
    print_banner()

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
    else:
        print("\n请选择操作:")
        print("  1. 清理构建目录")
        print("  2. 运行测试")
        print("  3. 检查代码质量")
        print("  4. 构建包")
        print("  5. 上传到 Test PyPI")
        print("  6. 上传到正式 PyPI")
        print("  7. 创建 Git 标签")
        print("  8. 完整发布流程")
        print("  9. 发布检查清单")
        print("  0. 退出")
        action = input("\n请选择 (0-9): ").strip()

    if action == "0" or action == "q":
        print("\n👋 再见!")
        return 0

    success = True

    if action in ["1", "clean"]:
        clean_build_dirs()

    elif action in ["2", "test"]:
        success = run_tests()

    elif action in ["3", "quality"]:
        check_code_quality()

    elif action in ["4", "build"]:
        clean_build_dirs()
        success = build_package()
        if success:
            show_build_artifacts()

    elif action in ["5", "testpypi"]:
        success = upload_to_pypi(test=True)

    elif action in ["6", "pypi"]:
        success = upload_to_pypi(test=False)

    elif action in ["7", "tag"]:
        success = create_git_tag()

    elif action in ["8", "full"]:
        print("\n🚀 开始完整发布流程...\n")

        clean_build_dirs()

        if not run_tests():
            print("\n❌ 测试失败，终止发布")
            return 1

        if not check_code_quality():
            print("\n⚠️  代码质量检查未完全通过，但继续...")

        if not build_package():
            print("\n❌ 构建失败，终止发布")
            return 1

        show_build_artifacts()

        print("\n" + "=" * 70)
        print("🎉 构建完成！")
        print("=" * 70)
        print("\n下一步操作:")
        print("  1. 测试安装: pip install dist/*.whl --force-reinstall")
        print("  2. 上传 Test: python release.py testpypi")
        print("  3. 上传正式: python release.py pypi")
        print("  4. 创建标签: python release.py tag")

    elif action in ["9", "checklist"]:
        print_release_checklist()

    else:
        print(f"\n❌ 无效的选择: {action}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
