# Docker 镜像构建与发布指南

本文档详细介绍如何构建、测试和发布 NFO to VSMETA 转换器的 Docker 镜像。

## 📋 目录

- [前置要求](#前置要求)
- [本地构建](#本地构建)
- [多架构构建](#多架构构建)
- [Docker Hub 发布](#docker-hub-发布)
- [GitHub Container Registry](#github-container-registry)
- [CI/CD 自动构建](#cicd-自动构建)
- [验证与测试](#验证与测试)

---

## 🔧 前置要求

### 1. 安装 Docker

**Linux (Ubuntu/Debian):**

```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker GPG 密钥
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**macOS:**

```bash
# 使用 Homebrew
brew install --cask docker
```

**Windows:**

下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 2. 验证安装

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker Compose 版本
docker compose version

# 运行测试容器
docker run hello-world
```

---

## 🐳 本地构建

### 1. 克隆项目

```bash
git clone https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA.git
cd TRAE--AI-NFO-to-VSMETA
```

### 2. 构建生产镜像

```bash
# 构建最新版本
docker build -t nfo-to-vsmeta:latest .

# 构建带版本号的镜像
docker build -t nfo-to-vsmeta:2.0.1 .
```

### 3. 构建开发镜像

```bash
docker build --target development -t nfo-to-vsmeta:dev .
```

### 4. 验证镜像

```bash
# 查看镜像
docker images | grep nfo-to-vsmeta

# 测试运行
docker run --rm nfo-to-vsmeta:latest --help
```

### 5. 使用 Docker Compose 构建

```bash
# 构建所有服务
docker compose build

# 构建特定服务
docker compose build converter
docker compose build webui
```

---

## 🛠️ 多架构构建

使用 Docker Buildx 构建多平台镜像。

### 1. 设置 Buildx

```bash
# 创建并使用新的 builder
docker buildx create --name mybuilder --use

# 查看可用平台
docker buildx inspect --bootstrap
```

### 2. 构建多架构镜像

```bash
# 构建 AMD64 和 ARM64 镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t nfo-to-vsmeta:latest \
  --push .

# 构建带版本号的镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t nfo-to-vsmeta:2.0.1 \
  -t nfo-to-vsmeta:latest \
  --push .
```

### 3. 本地构建不推送

```bash
# 构建并加载到本地 Docker
docker buildx build \
  --platform linux/amd64 \
  -t nfo-to-vsmeta:latest \
  --load .
```

---

## 🐙 Docker Hub 发布

### 1. 准备 Docker Hub 账户

- 注册 Docker Hub 账户: https://hub.docker.com/
- 创建仓库: `your-username/nfo-to-vsmeta`

### 2. 登录 Docker Hub

```bash
docker login

# 或使用访问令牌（推荐）
docker login -u your-username -p your-access-token
```

### 3. 标记镜像

```bash
# 标记为 Docker Hub 格式
docker tag nfo-to-vsmeta:latest your-username/nfo-to-vsmeta:latest
docker tag nfo-to-vsmeta:2.0.1 your-username/nfo-to-vsmeta:2.0.1
```

### 4. 推送镜像

```bash
# 推送 latest 标签
docker push your-username/nfo-to-vsmeta:latest

# 推送版本标签
docker push your-username/nfo-to-vsmeta:2.0.1
```

### 5. 完整发布流程

```bash
#!/bin/bash
# publish-docker.sh

set -e

VERSION="2.0.1"
DOCKER_USER="your-username"
IMAGE_NAME="nfo-to-vsmeta"

echo "🚀 开始构建和发布 Docker 镜像 v${VERSION}"

# 登录
docker login

# 构建多架构镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ${DOCKER_USER}/${IMAGE_NAME}:${VERSION} \
  -t ${DOCKER_USER}/${IMAGE_NAME}:latest \
  --push .

echo "✅ 发布完成!"
echo "📦 镜像: ${DOCKER_USER}/${IMAGE_NAME}"
echo "🏷️  标签: ${VERSION}, latest"
```

---

## 📦 GitHub Container Registry

### 1. 准备 GitHub Personal Access Token

- 创建 token: https://github.com/settings/tokens
- 需要权限: `write:packages`, `read:packages`, `delete:packages`

### 2. 登录 GHCR

```bash
# 登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u your-username --password-stdin
```

### 3. 标记和推送

```bash
# 标记镜像
docker tag nfo-to-vsmeta:latest ghcr.io/your-username/nfo-to-vsmeta:latest
docker tag nfo-to-vsmeta:2.0.1 ghcr.io/your-username/nfo-to-vsmeta:2.0.1

# 推送
docker push ghcr.io/your-username/nfo-to-vsmeta:latest
docker push ghcr.io/your-username/nfo-to-vsmeta:2.0.1
```

### 4. 使用 GHCR 镜像

```bash
docker pull ghcr.io/your-username/nfo-to-vsmeta:latest
```

---

## 🔄 CI/CD 自动构建

### GitHub Actions 示例

创建 `.github/workflows/docker.yml`:

```yaml
name: Docker

on:
  push:
    tags:
      - 'v*'
    branches:
      - main
  pull_request:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          platforms: linux/amd64,linux/arm64
```

---

## ✅ 验证与测试

### 1. 测试镜像功能

```bash
# 创建测试目录
mkdir -p test_movies test_output

# 运行转换测试
docker run --rm \
  -v $(pwd)/test_movies:/data/movies:ro \
  -v $(pwd)/test_output:/data/output \
  nfo-to-vsmeta:latest --help

# 测试 Web UI
docker run -d --name test-webui \
  -p 5000:5000 \
  nfo-to-vsmeta:latest web_ui

# 检查是否运行
docker ps | grep test-webui

# 清理
docker stop test-webui
docker rm test-webui
```

### 2. 使用 Docker Compose 测试

```bash
# 启动服务
docker compose up -d webui

# 查看日志
docker compose logs -f webui

# 测试访问
curl http://localhost:5000

# 停止服务
docker compose down
```

### 3. 安全扫描

```bash
# 使用 Trivy 扫描漏洞
trivy image nfo-to-vsmeta:latest

# 使用 Docker Scout
docker scout quickview nfo-to-vsmeta:latest
```

### 4. 性能测试

```bash
# 测试启动时间
time docker run --rm nfo-to-vsmeta:latest --version

# 测试镜像大小
docker images nfo-to-vsmeta --format "{{.Size}}"
```

---

## 📊 最佳实践

### 1. 镜像优化

- 使用多阶段构建（已实现）
- 使用 slim 镜像
- 清理 apt 缓存
- 只安装必要依赖

### 2. 版本管理

```bash
# 语义化版本
docker tag nfo-to-vsmeta:latest myrepo/nfo-to-vsmeta:2.0.1
docker tag nfo-to-vsmeta:latest myrepo/nfo-to-vsmeta:2.0
docker tag nfo-to-vsmeta:latest myrepo/nfo-to-vsmeta:2
```

### 3. 安全建议

- 定期更新基础镜像
- 扫描漏洞
- 使用非 root 用户（已实现）
- 签名镜像

---

## 🔧 故障排除

### 构建失败

```bash
# 查看详细日志
docker build --no-cache .

# 检查 Dockerfile 语法
docker build --quiet .
```

### 权限问题

```bash
# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 重新登录或重启
newgrp docker
```

### 空间不足

```bash
# 清理未使用的镜像
docker image prune -a

# 清理所有资源
docker system prune -a
```

---

## 📚 相关资源

- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [多架构构建](https://docs.docker.com/build/building/multi-platform/)
- [GitHub Actions for Docker](https://docs.docker.com/ci-cd/github-actions/)
- [Trivy 漏洞扫描](https://github.com/aquasecurity/trivy)

---

**需要帮助？** 创建 [Issue](https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA/issues)
