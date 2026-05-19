# Docker 快速参考指南

## 🐳 一句话快速启动

### 在您的本地机器上运行：

```bash
# 1. 克隆项目
git clone https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA.git
cd TRAE--AI-NFO-to-VSMETA

# 2. 运行完整发布脚本（推荐）- 支持 Docker Hub 和 GHCR！
./publish_docker.sh

# 或者只是构建（不发布）
./build_docker.sh
```

---

## 📦 三种使用方式

### 1️⃣ PyPI 安装（最简单）
```bash
pip install nfo-to-vsmeta[all]
nfo-to-vsmeta --help
```

### 2️⃣ Docker 容器运行
```bash
# 构建镜像
docker build -t nfo-to-vsmeta:latest .

# 运行命令行工具
docker run --rm nfo-to-vsmeta:latest --help

# 运行 Web UI
docker run -d -p 5000:5000 nfo-to-vsmeta:latest web_ui
```

### 3️⃣ Docker Compose
```bash
docker-compose up -d webui
```

---

## 🔄 发布到 Docker Hub

### 第 1 步：在 Docker Hub 创建仓库
1. 访问 https://hub.docker.com/repositories/create
2. 仓库名称: `nfo-to-vsmeta`
3. 可见度: 选择 **Public（公开）**
4. 点击 **Create**

### 第 2 步：使用发布脚本
```bash
./publish_docker.sh
# 选择选项 1（Docker Hub）
```

### 手动发布到 Docker Hub
```bash
# 登录
docker login -u your-dockerhub-username

# 构建并标记
docker build -t nfo-to-vsmeta:2.0.1 .
docker tag nfo-to-vsmeta:2.0.1 your-username/nfo-to-vsmeta:2.0.1
docker tag nfo-to-vsmeta:2.0.1 your-username/nfo-to-vsmeta:latest

# 推送
docker push your-username/nfo-to-vsmeta:2.0.1
docker push your-username/nfo-to-vsmeta:latest
```

### 使用 Docker Hub 镜像
```bash
# 拉取镜像
docker pull your-username/nfo-to-vsmeta:latest

# 运行
docker run --rm your-username/nfo-to-vsmeta:latest --help
```

---

## 🔄 发布到 GitHub Container Registry

### 准备 GitHub Personal Access Token (PAT)
1. 访问 https://github.com/settings/tokens
2. 生成新 token，选择 `write:packages` 权限
3. 保存您的 token

### 使用发布脚本
```bash
export GITHUB_TOKEN="your-token-here"
./publish_docker.sh
# 选择选项 2（GHCR）
```

### 手动发布到 GHCR
```bash
# 登录
echo "your-token" | docker login ghcr.io -u 1525745393 --password-stdin

# 构建并标记
docker build -t nfo-to-vsmeta:2.0.1 .
docker tag nfo-to-vsmeta:2.0.1 ghcr.io/1525745393/nfo-to-vsmeta:2.0.1
docker tag nfo-to-vsmeta:2.0.1 ghcr.io/1525745393/nfo-to-vsmeta:latest

# 推送
docker push ghcr.io/1525745393/nfo-to-vsmeta:2.0.1
docker push ghcr.io/1525745393/nfo-to-vsmeta:latest
```

### 使用 GHCR 镜像
```bash
# 拉取镜像
docker pull ghcr.io/1525745393/nfo-to-vsmeta:latest

# 运行
docker run --rm ghcr.io/1525745393/nfo-to-vsmeta:latest --help
```

---

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| **QUICKSTART_DOCKER.md** 🆕 | 本文件 - Docker 快速参考 |
| **DOCKER.md** | Docker 详细使用指南 |
| **DOCKER_BUILD.md** | Docker 构建发布详细指南 |
| **PROJECT_COMPLETE.md** | 完整项目总结 |
| **README.md** | 项目主使用文档 |

---

## 🎯 项目链接

- **GitHub**: https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA
- **PyPI**: https://pypi.org/project/nfo-to-vsmeta
- **GitHub Release**: https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA/releases

---

## 📖 完整功能

**NFO to VSMETA 转换器 v2.0.1 🎉


