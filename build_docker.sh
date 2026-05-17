#!/bin/bash
# NFO to VSMETA 转换器 Docker 镜像构建脚本

set -e

VERSION="2.0.1"
IMAGE_NAME="nfo-to-vsmeta"
DOCKER_HUB_USER="${DOCKER_HUB_USER:-yourusername}"

echo "========================================="
echo "  NFO to VSMETA 转换器 Docker 构建"
echo "  版本: $VERSION"
echo "========================================="
echo ""

# 清理旧的构建产物
echo "[1/5] 清理旧镜像..."
docker rmi $IMAGE_NAME:$VERSION 2>/dev/null || true
docker rmi $IMAGE_NAME:latest 2>/dev/null || true

# 构建镜像
echo ""
echo "[2/5] 构建 Docker 镜像..."
docker build -t $IMAGE_NAME:$VERSION .
docker tag $IMAGE_NAME:$VERSION $IMAGE_NAME:latest

# 测试镜像
echo ""
echo "[3/5] 测试镜像..."
docker run --rm $IMAGE_NAME:latest --version || docker run --rm $IMAGE_NAME:latest --help

# 显示镜像信息
echo ""
echo "[4/5] 镜像信息:"
docker images $IMAGE_NAME --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo ""
echo "[5/5] 完成！"
echo ""
echo "========================================="
echo "  使用方法:"
echo "========================================="
echo ""
echo "1. 运行命令行工具:"
echo "   docker run --rm -v \$(pwd)/movies:/data/movies:ro -v \$(pwd)/output:/data/output $IMAGE_NAME:latest -d /data/movies"
echo ""
echo "2. 运行 Web UI:"
echo "   docker run -d -p 5000:5000 -v \$(pwd)/movies:/data/movies:ro -v \$(pwd)/output:/data/output $IMAGE_NAME:latest web_ui"
echo ""
echo "3. 使用 Docker Compose:"
echo "   docker-compose up -d webui"
echo ""
echo "4. 推送到 Docker Hub（可选）:"
echo "   docker tag $IMAGE_NAME:latest $DOCKER_HUB_USER/$IMAGE_NAME:latest"
echo "   docker push $DOCKER_HUB_USER/$IMAGE_NAME:latest"
echo ""
echo "========================================="
