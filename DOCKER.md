# Docker 使用指南

本文档介绍如何使用 Docker 和 Docker Compose 运行 NFO to VSMETA 转换器。

## 📋 目录

- [快速开始](#快速开始)
- [Docker Compose 服务](#docker-compose-服务)
- [构建镜像](#构建镜像)
- [使用示例](#使用示例)
- [开发环境](#开发环境)
- [数据管理](#数据管理)
- [故障排除](#故障排除)

---

## 🚀 快速开始

### 1. 构建镜像

```bash
# 克隆项目
git clone https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA.git
cd nfo-to-vsmeta

# 构建生产镜像
docker build -t nfo-to-vsmeta:latest .

# 或使用 Docker Compose
docker-compose build
```

### 2. 运行转换

```bash
# 创建目录
mkdir -p movies output

# 将 NFO 文件放入 movies 目录
cp /path/to/your/movies/* movies/

# 运行转换
docker run -v $(pwd)/movies:/data/movies:ro \
           -v $(pwd)/output:/data/output \
           nfo-to-vsmeta:latest \
           -d /data/movies
```

---

## 🐳 Docker Compose 服务

我们提供了三个预配置的服务：

### 1. Converter（命令行转换器）

```bash
# 启动服务
docker-compose up converter

# 后台运行
docker-compose up -d converter

# 查看日志
docker-compose logs -f converter
```

### 2. Web UI（Web 界面）

```bash
# 启动服务
docker-compose up webui

# 后台运行
docker-compose up -d webui

# 访问
# http://localhost:5000
```

### 3. Development（开发环境）

```bash
# 启动开发环境
docker-compose up dev

# 进入容器
docker exec -it nfo-to-vsmeta-dev bash
```

---

## 🔨 构建镜像

### 生产镜像

```bash
docker build -t nfo-to-vsmeta:2.0.1 .
```

### 开发镜像

```bash
docker build --target development -t nfo-to-vsmeta:dev .
```

### 多架构构建（可选）

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t nfo-to-vsmeta:latest \
  --push .
```

---

## 📝 使用示例

### 示例 1: 基本转换

```bash
docker run -v $(pwd)/movies:/data/movies:ro \
           -v $(pwd)/output:/data/output \
           nfo-to-vsmeta:latest \
           -d /data/movies
```

### 示例 2: 指定线程数

```bash
docker run -v $(pwd)/movies:/data/movies:ro \
           -v $(pwd)/output:/data/output \
           nfo-to-vsmeta:latest \
           -d /data/movies --workers 8
```

### 示例 3: 覆盖已有文件

```bash
docker run -v $(pwd)/movies:/data/movies:ro \
           -v $(pwd)/output:/data/output \
           nfo-to-vsmeta:latest \
           -d /data/movies --overwrite
```

### 示例 4: Web UI

```bash
docker run -v $(pwd)/movies:/data/movies:ro \
           -v $(pwd)/output:/data/output \
           -p 5000:5000 \
           nfo-to-vsmeta:latest \
           web_ui
```

---

## 💻 开发环境

### 启动开发环境

```bash
# 使用 Docker Compose
docker-compose up dev

# 或手动构建和运行
docker build --target development -t nfo-to-vsmeta:dev .
docker run -it -v $(pwd):/app nfo-to-vsmeta:dev bash
```

### 在容器中运行测试

```bash
# 进入开发容器
docker exec -it nfo-to-vsmeta-dev bash

# 运行测试
pytest tests/ -v

# 格式化代码
black .

# 类型检查
mypy nfo_to_vsmeta_converter_complete.py
```

### 使用 IPython

```bash
docker exec -it nfo-to-vsmeta-dev ipython
```

---

## 📁 数据管理

### 目录结构

```
project/
├── movies/          # 输入：NFO 文件所在目录（只读挂载）
├── output/          # 输出：VSMETA 文件输出目录
├── config/          # 配置：持久化配置
└── data/            # 数据：缓存、日志等
```

### 权限问题

Docker 默认以非 root 用户运行。如果遇到权限问题：

```bash
# 修改本地目录权限
sudo chown -R 1000:1000 ./movies ./output ./config

# 或在运行时指定用户
docker run -u $(id -u):$(id -g) ...
```

### 数据备份

```bash
# 备份输出文件
tar czf backup_$(date +%Y%m%d).tar.gz output/

# 恢复备份
tar xzf backup_20240101.tar.gz
```

---

## ⚙️ 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TZ` | Asia/Shanghai | 时区 |
| `FLASK_ENV` | production | Flask 环境 |

### 持久化配置

创建 `config/config.json`：

```json
{
  "max_workers": 8,
  "max_image_size_kb": 200,
  "image_compression_ratio": 0.8,
  "retry_attempts": 3
}
```

然后挂载到容器：

```bash
docker run -v $(pwd)/config:/app/config \
           nfo-to-vsmeta:latest \
           ...
```

---

## 🔍 故障排除

### 常见问题

#### 1. 权限被拒绝

```
Permission denied: /data/output
```

解决：

```bash
# 方法 1: 修改目录权限
chmod 777 movies output

# 方法 2: 使用 --privileged
docker run --privileged ...

# 方法 3: 指定用户
docker run -u root ...
```

#### 2. 找不到文件

```
File not found: /data/movies
```

解决：确保挂载路径正确且文件存在

```bash
# 检查挂载
docker inspect nfo-to-vsmeta-converter | grep -A 10 Mounts
```

#### 3. 端口已被占用

```
Bind for 0.0.0.0:5000 failed: port is already allocated
```

解决：修改端口映射

```yaml
# docker-compose.yml
ports:
  - "5001:5000"  # 改为 5001
```

#### 4. 内存不足

```
Killed
```

解决：限制 Docker 内存使用

```bash
docker run --memory=1g nfo-to-vsmeta:latest ...
```

### 查看日志

```bash
# 查看所有日志
docker-compose logs

# 查看特定服务
docker-compose logs converter
docker-compose logs webui

# 实时跟踪
docker-compose logs -f

# 最近 100 行
docker-compose logs --tail=100
```

### 进入容器调试

```bash
# 进入运行中的容器
docker exec -it nfo-to-vsmeta-converter bash

# 检查 Python 版本
docker run nfo-to-vsmeta python --version

# 测试导入
docker run nfo-to-vsmeta python -c "import nfo_to_vsmeta_converter_complete"
```

---

## 🧹 清理

### 清理未使用的镜像

```bash
docker image prune -f
```

### 清理所有未使用的资源

```bash
docker system prune -a
```

### 清理构建缓存

```bash
docker builder prune -f
```

### 完全重置

```bash
# 停止所有容器
docker-compose down

# 删除所有相关资源
docker-compose down --rmi all -v --remove-orphans

# 删除构建缓存
docker builder prune -f
```

---

## 📊 性能优化

### 多线程配置

根据 CPU 核心数调整：

```bash
docker run -v $(pwd)/movies:/data/movies:ro \
           nfo-to-vsmeta:latest \
           -d /data/movies --workers 8
```

### 内存限制

```bash
# 限制内存
docker run --memory=2g nfo-to-vsmeta:latest ...

# 限制 CPU
docker run --cpus=2 nfo-to-vsmeta:latest ...
```

### GPU 加速（如果需要）

```bash
docker run --gpus all nfo-to-vsmeta:latest ...
```

---

## 🔒 安全建议

### 1. 使用只读挂载

```bash
# movies 目录只读
docker run -v $(pwd)/movies:/data/movies:ro ...
```

### 2. 避免以 root 运行

Docker 默认以非 root 用户运行（appuser），确保文件权限正确。

### 3. 定期更新镜像

```bash
# 重新构建
docker build --pull -t nfo-to-vsmeta:latest .

# 重新拉取
docker pull nfo-to-vsmeta:latest
```

---

## 📚 相关资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

## 🤝 获取帮助

如果你遇到问题：

1. 查看本文档的故障排除部分
2. 查看 [常见问题](../README.md#常见问题)
3. 创建 [Issue](https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA/issues)

---

**祝你使用愉快！🐳**
