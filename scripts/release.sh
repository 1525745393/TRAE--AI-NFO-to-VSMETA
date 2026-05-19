#!/bin/bash
# Quick Release Script
# 快速发布脚本 - 简化版本管理和发布流程

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    print_info "检查依赖..."
    if ! command -v git &> /dev/null; then
        print_error "git 未安装"
        exit 1
    fi
    if ! command -v python &> /dev/null; then
        print_error "python 未安装"
        exit 1
    fi
    print_info "依赖检查完成"
}

# Get current version
get_current_version() {
    python -c "
import re
with open('pyproject.toml', 'r', encoding='utf-8') as f:
    content = f.read()
version = re.search(r'version\s*=\s*\"([^\"]+)\"', content).group(1)
print(version)
"
}

# Confirm release
confirm_release() {
    local release_type=$1
    local new_version=$2

    echo ""
    echo "=========================================="
    echo "          发布确认"
    echo "=========================================="
    echo "发布类型: $release_type"
    echo "新版本号: $new_version"
    echo ""
    read -p "确认发布? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "发布已取消"
        exit 0
    fi
}

# Main function
main() {
    local release_type=${1:-patch}

    if [[ "$release_type" != "major" && "$release_type" != "minor" && "$release_type" != "patch" ]]; then
        print_error "无效的发布类型: $release_type"
        echo "使用方法: $0 [major|minor|patch]"
        exit 1
    fi

    check_dependencies

    local current_version=$(get_current_version)
    print_info "当前版本: $current_version"

    # Calculate new version
    python scripts/bump_version.py "$release_type" --dry-run

    # Wait for user confirmation
    read -p "继续发布? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "发布已取消"
        exit 0
    fi

    # Actual bump
    print_info "开始版本更新..."
    python scripts/bump_version.py "$release_type"

    print_info "✅ 版本更新完成！"
    echo ""
    echo "下一步操作:"
    echo "  1. 检查更改: git diff HEAD~1"
    echo "  2. 推送到 GitHub: git push && git push --tags"
    echo "  3. 等待 CI/CD 自动完成发布"
    echo ""
}

main "$@"
