#!/usr/bin/env python3
"""
使用 GitHub API 创建 Release 的脚本
"""

import sys
import requests
from pathlib import Path


def get_github_token():
    """从 git remote 中提取 GitHub token"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        if "@github.com" in url:
            # 格式: https://token@github.com/owner/repo
            token_part = url.split("https://")[1].split("@github.com")[0]
            if ":" in token_part:
                token = token_part.split(":")[1]
            else:
                token = token_part
            return token
    except Exception as e:
        print(f"无法提取 token: {e}", file=sys.stderr)
    return None


def get_repo_info():
    """获取仓库信息"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        if url.endswith(".git"):
            url = url[:-4]
        # 提取 owner 和 repo
        if "@github.com" in url:
            path = url.split("@github.com/")[1]
        elif "github.com/" in url:
            path = url.split("github.com/")[1]
        else:
            return None, None
        parts = path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    except Exception as e:
        print(f"无法获取仓库信息: {e}", file=sys.stderr)
    return None, None


def create_release(token, owner, repo, tag, name, body, files):
    """创建 GitHub Release"""
    base_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. 创建 Release
    release_url = f"{base_url}/releases"
    release_data = {
        "tag_name": tag,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False
    }

    print(f"创建 Release: {tag}...")
    response = requests.post(release_url, headers=headers, json=release_data, timeout=30)

    if response.status_code == 201:
        release = response.json()
        print(f"✅ Release 创建成功: {release['html_url']}")
        release_id = release["id"]
        upload_url = release["upload_url"].replace("{?name,label}", "")
    elif response.status_code == 422:
        print("⚠️  Release 已存在，尝试获取现有 Release...")
        # 尝试获取现有 Release
        response = requests.get(f"{release_url}/tags/{tag}", headers=headers, timeout=30)
        if response.status_code == 200:
            release = response.json()
            print(f"找到现有 Release: {release['html_url']}")
            release_id = release["id"]
            upload_url = release["upload_url"].replace("{?name,label}", "")
        else:
            print(f"❌ 无法获取 Release: {response.status_code}")
            print(response.text)
            return False
    else:
        print(f"❌ 创建 Release 失败: {response.status_code}")
        print(response.text)
        return False

    # 2. 上传文件
    if files:
        print("\n上传构建产物...")
        for file_path in files:
            path = Path(file_path)
            if not path.exists():
                print(f"⚠️  文件不存在: {file_path}")
                continue

            print(f"上传: {path.name}...")
            file_headers = {
                "Authorization": f"token {token}",
                "Content-Type": "application/octet-stream"
            }
            params = {"name": path.name}

            with open(path, "rb") as f:
                upload_response = requests.post(
                    upload_url,
                    headers=file_headers,
                    params=params,
                    data=f,
                    timeout=60
                )

            if upload_response.status_code == 201:
                print(f"✅ {path.name} 上传成功")
            else:
                print(f"❌ {path.name} 上传失败: {upload_response.status_code}")
                print(upload_response.text)

    print("\n🎉 Release 完成!")
    print(f"访问: {release['html_url']}")
    return True


def main():
    token = get_github_token()
    if not token:
        print("❌ 无法获取 GitHub token", file=sys.stderr)
        return 1

    owner, repo = get_repo_info()
    if not owner or not repo:
        print("❌ 无法获取仓库信息", file=sys.stderr)
        return 1

    print(f"仓库: {owner}/{repo}")

    tag = "v2.0.1"
    name = "v2.0.1 - 插件系统优化"
    body = """## 🎉 新功能

- **插件系统优化**
  - ✅ 实现插件依赖管理和拓扑排序
  - ✅ 实现插件优先级控制系统（0-100）
  - ✅ 实现插件配置持久化（PluginConfig）
  - ✅ 实现插件热重载功能（watchdog）
  - ✅ 实现插件模板生成器

## ✨ 改进

- 优化插件加载流程
- 改进插件注册机制
- 增强错误处理和日志记录
- Web UI 插件管理界面增强

## 🐛 修复

- 修复插件优先级排序问题
- 修复配置文件加载问题

---

## 📦 安装方式

### PyPI (推荐)
```bash
pip install nfo-to-vsmeta[all]
```

### 从源码安装
```bash
pip install nfo_to_vsmeta-2.0.1-py3-none-any.whl
```
"""

    files = [
        "dist/nfo_to_vsmeta-2.0.1.tar.gz",
        "dist/nfo_to_vsmeta-2.0.1-py3-none-any.whl"
    ]

    success = create_release(token, owner, repo, tag, name, body, files)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
