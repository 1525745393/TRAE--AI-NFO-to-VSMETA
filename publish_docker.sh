#!/bin/bash
# NFO to VSMETA 转换器 Docker 镜像完整发布脚本
# 此脚本用于在您的本地机器上完整构建和发布 Docker 镜像

set -e

VERSION="2.0.1"
IMAGE_NAME="nfo-to-vsmeta"
GITHUB_USER="${GITHUB_USER:-1525745393}"
GITHUB_REPO="${GITHUB_REPO:-TRAE--AI-NFO-to-VSMETA}"

echo "========================================="
echo "  NFO to VSMETA 转换器"
echo "  Docker 镜像完整发布"
echo "  版本: $VERSION"
echo "========================================="
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
echo -e "${YELLOW}[1/8] 检查环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo -e "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已安装${NC}"
docker --version
echo ""

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误: Docker 未运行${NC}"
    echo -e "请先启动 Docker 服务"
    exit 1
fi
echo -e "${GREEN}✓ Docker 正在运行${NC}"
echo ""

# 清理旧镜像
echo -e "${YELLOW}[2/8] 清理旧镜像...${NC}"
docker rmi $IMAGE_NAME:$VERSION 2>/dev/null || true
docker rmi $IMAGE_NAME:latest 2>/dev/null || true
docker rmi ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION 2>/dev/null || true
docker rmi ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest 2>/dev/null || true
echo -e "${GREEN}✓ 清理完成${NC}"
echo ""

# 构建镜像
echo -e "${YELLOW}[3/8] 构建 Docker 镜像...${NC}"
docker build -t $IMAGE_NAME:$VERSION .
docker tag $IMAGE_NAME:$VERSION $IMAGE_NAME:latest
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 测试镜像
echo -e "${YELLOW}[4/8] 测试镜像功能...${NC}"
docker run --rm $IMAGE_NAME:latest --version || docker run --rm $IMAGE_NAME:latest --help
echo -e "${GREEN}✓ 镜像测试通过${NC}"
echo ""

# 显示镜像信息
echo -e "${YELLOW}[5/8] 镜像信息:${NC}"
docker images $IMAGE_NAME --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""

# 询问是否要发布到 GitHub Container Registry
echo -e "${YELLOW}[6/8] 准备发布...${NC}"
read -p "是否要发布到 GitHub Container Registry? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}发布到 GitHub Container Registry${NC}"
    echo ""
    
    # 检查 GitHub Token
    if [ -z "$GITHUB_TOKEN" ]; then
        echo -e "${YELLOW}请输入您的 GitHub Personal Access Token (需要 write:packages 权限):${NC}"
        read -s GITHUB_TOKEN
        echo ""
    fi
    
    # 登录 GHCR
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u $GITHUB_USER --password-stdin
    
    # 标记镜像
    docker tag $IMAGE_NAME:$VERSION ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION
    docker tag $IMAGE_NAME:latest ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest
    
    # 推送镜像
    echo ""
    echo -e "${YELLOW}[7/8] 推送镜像...${NC}"
    docker push ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION
    docker push ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest
    echo -e "${GREEN}✓ 镜像推送到 GitHub Container Registry 完成${NC}"
    echo ""
    
    # 显示拉取命令
    echo -e "${YELLOW}[8/8] 完成！${NC}"
    echo ""
    echo "========================================="
    echo "  使用拉取命令:"
    echo "========================================="
    echo ""
    echo "docker pull ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION"
    echo "docker pull ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest"
    echo ""
    echo "========================================="
    echo "  运行容器:"
    echo "========================================="
    echo ""
    echo "# 命令行工具"
    echo "docker run --rm ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest --help"
    echo ""
    echo "# Web UI"
    echo "docker run -d -p 5000:5000 ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest web_ui"
    echo ""
else
    echo ""
    echo -e "${GREEN}✓ 跳过发布${NC}"
    echo ""
    echo -e "${YELLOW}[7/8] 本地镜像使用方法:${NC}"
    echo ""
    echo "# 命令行工具"
    echo "docker run --rm $IMAGE_NAME:latest --help"
    echo ""
    echo "# Web UI"
    echo "docker run -d -p 5000:5000 $IMAGE_NAME:latest web_ui"
    echo ""
fi

echo ""
echo "========================================="
echo "  🎉 Docker 镜像发布完成！"
echo "========================================="
echo ""
echo "访问项目 GitHub: https://github.com/$GITHUB_USER/$GITHUB_REPO"
echo ""
