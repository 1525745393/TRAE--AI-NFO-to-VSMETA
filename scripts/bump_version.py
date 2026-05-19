#!/usr/bin/env python3
"""
自动版本管理和发布工具
用于自动更新版本号、CHANGELOG 和创建发布
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

VERSION_FILE = "pyproject.toml"
CHANGELOG_FILE = "CHANGELOG.md"


def get_current_version() -> str:
    """获取当前版本号"""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    raise ValueError("Version not found in pyproject.toml")


def bump_version(version: str, release_type: str) -> str:
    """
    版本号递增

    Args:
        version: 当前版本号 (如 "1.2.3")
        release_type: 发布类型 (major/minor/patch)

    Returns:
        新版本号
    """
    major, minor, patch = map(int, version.split("."))

    if release_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif release_type == "minor":
        minor += 1
        patch = 0
    elif release_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid release type: {release_type}")

    return f"{major}.{minor}.{patch}"


def update_pyproject_version(new_version: str) -> None:
    """更新 pyproject.toml 中的版本号"""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r'version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content
    )

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)


def update_changelog(new_version: str) -> None:
    """更新 CHANGELOG.md"""
    today = datetime.now().strftime("%Y-%m-%d")

    with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找是否已有未发布的版本
    unreleased_pattern = r"## \[Unreleased\](.*?)(?=\n## \[)"
    unreleased_match = re.search(unreleased_pattern, content, re.DOTALL)

    if unreleased_match:
        # 将 Unreleased 替换为新版本
        unreleased_content = unreleased_match.group(1)
        new_section = f"## [{new_version}] - {today}\n{unreleased_content}"

        # 添加新的 Unreleased 部分
        new_unreleased = "## [Unreleased]\n\n### 🎉 新功能\n\n### ✨ 改进\n\n### 🐛 修复\n\n---\n\n"
        content = content.replace(f"## [Unreleased]{unreleased_content}", new_unreleased + new_section)
    else:
        # 如果没有 Unreleased，在开头添加新版本
        header = "# 更新日志\n\n"
        new_section = f"## [{new_version}] - {today}\n\n### 🎉 新功能\n\n- 待补充\n\n### ✨ 改进\n\n### 🐛 修复\n\n---\n\n"
        content = header + new_section + content[len(header):]

    with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def create_git_tag(version: str) -> None:
    """创建 git tag"""
    import subprocess
    subprocess.run(["git", "add", VERSION_FILE, CHANGELOG_FILE], check=True)
    subprocess.run(["git", "commit", "-m", f"chore: bump version to {version}"], check=True)
    subprocess.run(["git", "tag", f"v{version}"], check=True)
    print(f"✓ Created git tag v{version}")


def main():
    parser = argparse.ArgumentParser(description="自动版本管理和发布工具")
    parser.add_argument(
        "release_type",
        choices=["major", "minor", "patch"],
        help="发布类型: major (主版本), minor (次版本), patch (补丁)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行，不实际修改文件"
    )

    args = parser.parse_args()

    try:
        current_version = get_current_version()
        print(f"当前版本: {current_version}")

        new_version = bump_version(current_version, args.release_type)
        print(f"新版本: {new_version}")

        if args.dry_run:
            print("试运行模式，不修改文件")
            return

        print(f"\n开始更新版本到 {new_version}...")

        update_pyproject_version(new_version)
        print("✓ 更新 pyproject.toml")

        update_changelog(new_version)
        print("✓ 更新 CHANGELOG.md")

        create_git_tag(new_version)

        print(f"\n✅ 发布准备完成！")
        print(f"执行以下命令完成发布:")
        print(f"  git push && git push --tags")

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
