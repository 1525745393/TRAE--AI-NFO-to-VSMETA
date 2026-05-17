# Docker 发布指南

本指南说明如何配置 Docker Hub 自动构建和发布流程。

## 目录

- [1. 准备 Docker Hub 账户](#1-准备-docker-hub-账户)
- [2. 配置 GitHub Secrets](#2-配置-github-secrets)
- [3. 自动发布流程](#3-自动发布流程)
- [4. 手动构建和发布](#4-手动构建和发布)
- [5. 使用 Docker 镜像](#5-使用-docker-镜像)

---

## 1. 准备 Docker Hub 账户

### 步骤 1：创建 Docker Hub 账户（如需要）

访问 [Docker Hub](https://hub.docker.com/) 并注册账户。

### 步骤 2：创建仓库

1. 登录 Docker Hub
2. 点击 **Create Repository**
3. **Repository Name**: `nfo-to-vsmeta`
4. **Visibility**: Public（或 Private）
5. 点击 **Create**

### 步骤 3：生成访问令牌（推荐）

为了安全，使用访问令牌而不是密码：

1. 点击右上角用户名 → **Account Settings**
2. 选择 **Security** → **New Access Token**
3. **Token Description**: `GitHub Actions CI/CD`
4. **Access Permissions**: Read, Write, Delete
5. 点击 **Generate**
6. **重要**：立即复制令牌，只显示一次！

---

## 2. 配置 GitHub Secrets

### 在仓库中添加 Docker Hub 凭证

1. 打开 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，添加以下 Secrets：

#### Secret 1: `DOCKER_USERNAME`
- **Name**: `DOCKER_USERNAME`
- **Value**: 您的 Docker Hub 用户名

#### Secret 2: `DOCKER_PASSWORD`
- **Name**: `DOCKER_PASSWORD`
- **Value**: 您的 Docker Hub 密码或访问令牌（推荐使用访问令牌）

### 验证 Secrets 配置

确认仓库有以下 Secrets：
- `DOCKER_USERNAME` - Docker Hub 用户名
- `DOCKER_PASSWORD` - Docker Hub 密码或访问令牌
- `PYPI_API_TOKEN` - PyPI API 令牌（之前已配置）
- `TEST_PYPI_API_TOKEN` - Test PyPI 令牌（之前已配置）

---

## 3. 自动发布流程

### 触发条件

Docker 镜像构建和发布在以下情况自动触发：
- 推送到 `main` 分支时
- 推送以 `v` 开头的标签时（如 `v1.0.0`、`v2.0.1`）

### 自动标签策略

GitHub Actions 会自动生成以下标签：

| 触发事件 | 标签示例 |
|---------|---------|
| main 分支推送 | `latest`, `sha-abc123` |
| 标签 v2.0.2 | `2.0.2`, `2.0`, `2`, `latest` |
| Pull Request | `pr-123` |

### 支持的平台

- `linux/amd64` - x86_64 架构（常见服务器、PC）
- `linux/arm64` - ARM64 架构（树莓派、Mac M1/M2/M3）

---

## 4. 手动构建和发布

### 本地构建镜像

```bash
# 构建生产镜像
docker build -t nfo-to-vsmeta:latest .

# 构建多架构镜像（使用 buildx）
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourusername/nfo-to-vsmeta:latest \
  --push .
```

### 本地测试镜像

```bash
# 测试运行
docker run --rm nfo-to-vsmeta:latest --help

# 测试 Web UI
docker run -d -p 5000:5000 --entrypoint python nfo-to-vsmeta:latest web_ui.py
# 访问 http://localhost:5000
```

### 手动推送到 Docker Hub

```bash
# 登录
docker login

# 打标签
docker tag nfo-to-vsmeta:latest yourusername/nfo-to-vsmeta:latest
docker tag nfo-to-vsmeta:latest yourusername/nfo-to-vsmeta:2.0.2

# 推送
docker push yourusername/nfo-to-vsmeta:latest
docker push yourusername/nfo-to-vsmeta:2.0.2
```

---

## 5. 使用 Docker 镜像

### 快速开始

#### 命令行模式

```bash
# 基本用法
docker run --rm -v /path/to/movies:/data \
  yourusername/nfo-to-vsmeta:latest -d /data

# 指定输出目录
docker run --rm -v /path/to/movies:/data:ro -v /path/to/output:/output \
  yourusername/nfo-to-vsmeta:latest -d /data -o /output

# 启用多线程
docker run --rm -v /path/to/movies:/data \
  yourusername/nfo-to-vsmeta:latest -d /data --workers 8
```

#### Web UI 模式

```bash
docker run -d \
  -p 5000:5000 \
  -v /path/to/movies:/data:ro \
  -v /path/to/output:/output \
  --name nfo-to-vsmeta-webui \
  --entrypoint python \
  yourusername/nfo-to-vsmeta:latest web_ui.py
```

访问：http://localhost:5000

### 使用 Docker Compose

项目包含了 [`docker-compose.yml`](docker-compose.yml)，可以直接使用：

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

自定义配置请参考 [`docker-compose.yml`](docker-compose.yml) 文件。

### 生产环境部署建议

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  converter:
    image: yourusername/nfo-to-vsmeta:latest
    container_name: nfo-to-vsmeta-converter
    restart: unless-stopped
    volumes:
      - /your/media/path:/data:ro
      - ./output:/output
    command: ["-d", "/data", "-o", "/output", "--workers", "4"]
    environment:
      - TZ=Asia/Shanghai

  webui:
    image: yourusername/nfo-to-vsmeta:latest
    container_name: nfo-to-vsmeta-webui
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - /your/media/path:/data:ro
      - ./output:/output
    environment:
      - TZ=Asia/Shanghai
      - FLASK_ENV=production
    entrypoint: ["python", "web_ui.py"]
```

---

## CI/CD 配置说明

已更新的 [`.github/workflows/ci.yml`](.github/workflows/ci.yml) 中的 Docker 配置：

```yaml
docker-build:
  name: Build and Push Docker Image
  runs-on: ubuntu-latest
  needs: [test, quality-check]
  if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v'))

  steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      
    - name: Log in to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
        
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ secrets.DOCKER_USERNAME }}/nfo-to-vsmeta
        tags: |
          type=ref,event=branch
          type=semver,pattern={{version}}
          type=raw,value=latest,enable={{is_default_branch}}
          
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        platforms: linux/amd64,linux/arm64
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

---

## 完整发布示例

### 发布版本 v2.0.2

```bash
# 1. 确保代码最新
git checkout main
git pull origin main

# 2. 运行所有测试（可选但推荐）
pytest tests/ -v

# 3. 创建标签
git tag -a v2.0.2 -m "Release version 2.0.2"

# 4. 推送标签
git push origin v2.0.2

# 5. 监控 GitHub Actions
# 访问仓库的 Actions 标签页查看构建进度
```

完成后，以下镜像将自动发布到 Docker Hub：
- `yourusername/nfo-to-vsmeta:2.0.2`
- `yourusername/nfo-to-vsmeta:2.0`
- `yourusername/nfo-to-vsmeta:2`
- `yourusername/nfo-to-vsmeta:latest`

---

## 安全最佳实践

1. **使用 Docker Hub 访问令牌** 而不是密码
2. **不要将凭证提交到代码仓库**
3. **定期轮换访问令牌**
4. **限制 GitHub Secrets 的访问权限**
5. **扫描镜像漏洞**（可集成 Trivy 等工具）
6. **使用最小权限原则**

---

## 故障排除

### 构建失败

1. 检查 GitHub Actions 日志
2. 确认 `DOCKER_USERNAME` 和 `DOCKER_PASSWORD` 配置正确
3. 确认 Docker Hub 仓库名称正确
4. 检查 Dockerfile 是否有语法错误

### 推送失败

1. 确认 Docker Hub 访问令牌有效且有写入权限
2. 确认仓库名称正确
3. 检查网络连接

### 镜像拉取失败

1. 确认仓库是公开的，或已登录
2. 检查镜像名称和标签是否正确
3. 确认平台兼容性

---

## 相关资源

- [Docker Hub 文档](https://docs.docker.com/docker-hub/)
- [GitHub Actions Docker 指南](https://docs.docker.com/ci-cd/github-actions/)
- [Docker 官方文档](https://docs.docker.com/)
- [项目 Dockerfile](Dockerfile)
- [Docker Compose 配置](docker-compose.yml)
