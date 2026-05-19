#!/bin/bash
# NFO to VSMETA 转换器 Docker 镜像完整发布脚本
# 此脚本用于在您的本地机器上完整构建和发布 Docker 镜像

set -e

VERSION="2.0.1"
IMAGE_NAME="nfo-to-vsmeta"
GITHUB_USER="${GITHUB_USER:-1525745393}"
GITHUB_REPO="${GITHUB_REPO:-TRAE--AI-NFO-to-VSMETA}"
DOCKER_HUB_USER="${DOCKER_HUB_USER:-$GITHUB_USER}"

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
echo -e "${YELLOW}[1/10] 检查环境...${NC}"
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
echo -e "${YELLOW}[2/10] 清理旧镜像...${NC}"
docker rmi $IMAGE_NAME:$VERSION 2>/dev/null || true
docker rmi $IMAGE_NAME:latest 2>/dev/null || true
docker rmi ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION 2>/dev/null || true
docker rmi ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest 2>/dev/null || true
docker rmi $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION 2>/dev/null || true
docker rmi $DOCKER_HUB_USER/$IMAGE_NAME:latest 2>/dev/null || true
echo -e "${GREEN}✓ 清理完成${NC}"
echo ""

# 构建镜像
echo -e "${YELLOW}[3/10] 构建 Docker 镜像...${NC}"
docker build -t $IMAGE_NAME:$VERSION .
docker tag $IMAGE_NAME:$VERSION $IMAGE_NAME:latest
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 测试镜像
echo -e "${YELLOW}[4/10] 测试镜像功能...${NC}"
docker run --rm $IMAGE_NAME:latest --version || docker run --rm $IMAGE_NAME:latest --help
echo -e "${GREEN}✓ 镜像测试通过${NC}"
echo ""

# 显示镜像信息
echo -e "${YELLOW}[5/10] 镜像信息:${NC}"
docker images $IMAGE_NAME --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""

# 询问发布目标
echo -e "${YELLOW}[6/10] 选择发布目标...${NC}"
echo "请选择发布目标:"
echo "1) Docker Hub"
echo "2) GitHub Container Registry (GHCR)"
echo "3) 两者都发布"
echo "4) 仅本地构建，不发布"
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}发布到 Docker Hub${NC}"
        echo ""
        
        # 检查 Docker Hub 用户名
        if [ -z "$DOCKER_HUB_USER" ] || [ "$DOCKER_HUB_USER" = "1525745393" ]; then
            echo -e "${YELLOW}请输入您的 Docker Hub 用户名:${NC}"
            read DOCKER_HUB_USER
        fi
        
        # 登录 Docker Hub
        echo -e "${YELLOW}请输入您的 Docker Hub 密码或访问令牌:${NC}"
        docker login -u $DOCKER_HUB_USER
        
        # 标记镜像
        docker tag $IMAGE_NAME:$VERSION $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION
        docker tag $IMAGE_NAME:latest $DOCKER_HUB_USER/$IMAGE_NAME:latest
        
        # 推送镜像
        echo ""
        echo -e "${YELLOW}[7/10] 推送镜像...${NC}"
        docker push $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION
        docker push $DOCKER_HUB_USER/$IMAGE_NAME:latest
        echo -e "${GREEN}✓ 镜像推送到 Docker Hub 完成${NC}"
        echo ""
        
        # 显示拉取命令
        echo -e "${YELLOW}[8/10] 完成！${NC}"
        echo ""
        echo "========================================="
        echo "  使用拉取命令:"
        echo "========================================="
        echo ""
        echo "docker pull $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION"
        echo "docker pull $DOCKER_HUB_USER/$IMAGE_NAME:latest"
        echo ""
        echo "========================================="
        echo "  运行容器:"
        echo "========================================="
        echo ""
        echo "# 命令行工具"
        echo "docker run --rm $DOCKER_HUB_USER/$IMAGE_NAME:latest --help"
        echo ""
        echo "# Web UI"
        echo "docker run -d -p 5000:5000 $DOCKER_HUB_USER/$IMAGE_NAME:latest web_ui"
        echo ""
        ;;
    
    2)
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
        echo -e "${YELLOW}[7/10] 推送镜像...${NC}"
        docker push ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION
        docker push ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest
        echo -e "${GREEN}✓ 镜像推送到 GitHub Container Registry 完成${NC}"
        echo ""
        
        # 显示拉取命令
        echo -e "${YELLOW}[8/10] 完成！${NC}"
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
        ;;
    
    3)
        echo ""
        echo -e "${YELLOW}发布到 Docker Hub 和 GitHub Container Registry${NC}"
        echo ""
        
        # 检查 Docker Hub 用户名
        if [ -z "$DOCKER_HUB_USER" ] || [ "$DOCKER_HUB_USER" = "1525745393" ]; then
            echo -e "${YELLOW}请输入您的 Docker Hub 用户名:${NC}"
            read DOCKER_HUB_USER
        fi
        
        # 登录 Docker Hub
        echo -e "${YELLOW}[7/10] 登录 Docker Hub...${NC}"
        echo -e "请输入您的 Docker Hub 密码或访问令牌:${NC}"
        docker login -u $DOCKER_HUB_USER
        
        # 标记和推送 Docker Hub
        docker tag $IMAGE_NAME:$VERSION $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION
        docker tag $IMAGE_NAME:latest $DOCKER_HUB_USER/$IMAGE_NAME:latest
        echo ""
        echo -e "${YELLOW}[8/10] 推送到 Docker Hub...${NC}"
        docker push $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION
        docker push $DOCKER_HUB_USER/$IMAGE_NAME:latest
        echo -e "${GREEN}✓ 镜像推送到 Docker Hub 完成${NC}"
        echo ""
        
        # 检查 GitHub Token
        if [ -z "$GITHUB_TOKEN" ]; then
            echo -e "${YELLOW}请输入您的 GitHub Personal Access Token (需要 write:packages 权限):${NC}"
            read -s GITHUB_TOKEN
            echo ""
        fi
        
        # 登录 GHCR
        echo "$GITHUB_TOKEN" | docker login ghcr.io -u $GITHUB_USER --password-stdin
        
        # 标记和推送 GHCR
        docker tag $IMAGE_NAME:$VERSION ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION
        docker tag $IMAGE_NAME:latest ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest
        echo ""
        echo -e "${YELLOW}[9/10] 推送到 GitHub Container Registry...${NC}"
        docker push ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION
        docker push ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest
        echo -e "${GREEN}✓ 镜像推送到 GitHub Container Registry 完成${NC}"
        echo ""
        
        # 显示拉取命令
        echo -e "${YELLOW}[10/10] 完成！${NC}"
        echo ""
        echo "========================================="
        echo "  使用拉取命令:"
        echo "========================================="
        echo ""
        echo "## Docker Hub:"
        echo "docker pull $DOCKER_HUB_USER/$IMAGE_NAME:$VERSION"
        echo "docker pull $DOCKER_HUB_USER/$IMAGE_NAME:latest"
        echo ""
        echo "## GitHub Container Registry:"
        echo "docker pull ghcr.io/$GITHUB_USER/$IMAGE_NAME:$VERSION"
        echo "docker pull ghcr.io/$GITHUB_USER/$IMAGE_NAME:latest"
        echo ""
        ;;
    
    *)
        echo ""
        echo -e "${GREEN}✓ 仅本地构建完成${NC}"
        echo ""
        echo -e "${YELLOW}[7/10] 本地镜像使用方法:${NC}"
        echo ""
        echo "# 命令行工具"
        echo "docker run --rm $IMAGE_NAME:latest --help"
        echo ""
        echo "# Web UI"
        echo "docker run -d -p 5000:5000 $IMAGE_NAME:latest web_ui"
        echo ""
        ;;
esac

echo ""
echo "========================================="
echo "  🎉 Docker 镜像构建完成！"
echo "========================================="
echo ""
echo "访问项目 GitHub: https://github.com/$GITHUB_USER/$GITHUB_REPO"
echo ""

