# PyPI 发布和 Docker 支持 - 完整指南

本指南包含将 NFO to VSMETA 转换器发布到 PyPI 和使用 Docker 的所有信息。

## 📋 目录

1. [PyPI 发布](#pypi-发布)
2. [Docker 支持](#docker-支持)
3. [快速开始](#快速开始)
4. [发布检查清单](#发布检查清单)

---

## 🚀 PyPI 发布

### 创建的文件

1. ✅ `pyproject.toml` - 项目配置（已优化）
2. ✅ `MANIFEST.in` - 打包清单
3. ✅ `release.py` - 发布脚本
4. ✅ `RELEASE_GUIDE.md` - 发布指南

### 发布命令

#### 方法 1: 使用发布脚本

```bash
# 1. 清理和测试
python release.py full

# 2. 上传到 Test PyPI
python release.py testpypi

# 3. 测试安装
pip install --index-url https://test.pypi.org/simple/ nfo-to-vsmeta

# 4. 上传到正式 PyPI
python release.py pypi

# 5. 创建 Git 标签
python release.py tag
```

#### 方法 2: 手动发布

```bash
# 1. 安装工具
pip install --upgrade build twine

# 2. 清理
rm -rf build/ dist/ *.egg-info

# 3. 构建
python -m build

# 4. 上传到 Test PyPI
twine upload --repository testpypi dist/*

# 5. 上传到正式 PyPI
twine upload dist/*
```

### PyPI 账户准备

1. **Test PyPI**: https://test.pypi.org/account/register/
2. **正式 PyPI**: https://pypi.org/account/register/
3. **创建 API Token**: https://pypi.org/manage/account/#api-tokens

### 配置凭证

创建 `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxxxxxxxxxxxxxxx
```

---

## 🐳 Docker 支持

### 创建的文件

1. ✅ `Dockerfile` - 多阶段构建（优化镜像大小）
2. ✅ `docker-compose.yml` - 编排配置
3. ✅ `.dockerignore` - Docker 忽略规则
4. ✅ `DOCKER.md` - Docker 使用指南

### Docker 快速开始

#### 构建镜像

```bash
# 构建生产镜像
docker build -t nfo-to-vsmeta:latest .

# 构建开发镜像
docker build --target development -t nfo-to-vsmeta:dev .
```

#### 运行容器

```bash
# 命令行转换
docker run -v $(pwd)/movies:/data/movies:ro \
           -v $(pwd)/output:/data/output \
           nfo-to-vsmeta:latest \
           -d /data/movies

# Web UI
docker run -p 5000:5000 \
           -v $(pwd)/movies:/data/movies:ro \
           nfo-to-vsmeta:latest \
           web_ui
```

#### 使用 Docker Compose

```bash
# 启动 Web UI
docker-compose up -d webui

# 访问
open http://localhost:5000

# 查看日志
docker-compose logs -f webui

# 停止
docker-compose down
```

### Docker Compose 服务

| 服务 | 说明 | 命令 |
|------|------|------|
| `converter` | 命令行转换器 | `docker-compose up converter` |
| `webui` | Web 界面 | `docker-compose up -d webui` |
| `dev` | 开发环境 | `docker-compose up dev` |

---

## ⚡ 快速开始

### 选项 1: 直接安装

```bash
# 安装
pip install nfo-to-vsmeta

# 运行
nfo-to-vsmeta -d /path/to/movies

# Web UI
nfo-vsmeta-web
```

### 选项 2: Docker

```bash
# 拉取镜像
docker pull nfo-to-vsmeta:latest

# 运行
docker run -v $(pwd)/movies:/data/movies nfo-to-vsmeta:latest
```

### 选项 3: 从源码

```bash
# 克隆
git clone https://github.com/example/nfo-to-vsmeta.git
cd nfo-to-vsmeta

# 安装依赖
pip install -r requirements.txt

# 运行
python nfo_to_vsmeta_converter_complete.py -d /path/to/movies
```

---

## ✅ 发布检查清单

### 代码准备

- [ ] 所有功能完成
- [ ] 所有测试通过 (`pytest tests/`)
- [ ] 代码格式化 (`black .`)
- [ ] 类型检查通过 (`mypy .`)
- [ ] Lint 检查通过 (`flake8 .`)

### 文档检查

- [ ] README.md 已更新
- [ ] CHANGELOG.md 已更新
- [ ] 版本号已更新（pyproject.toml）
- [ ] LICENSE 文件正确

### Git 准备

- [ ] 所有更改已提交
- [ ] 版本标签已创建 (`git tag v2.0.1`)
- [ ] 推送到远程 (`git push`)

### PyPI 准备

- [ ] Test PyPI 账户已创建
- [ ] 正式 PyPI 账户已创建
- [ ] API Token 已生成
- [ ] `.pypirc` 已配置

### Test PyPI 测试

- [ ] 构建成功
- [ ] 上传到 Test PyPI
- [ ] Test PyPI 安装测试
- [ ] 功能测试通过

### 正式发布

- [ ] 上传到正式 PyPI
- [ ] 正式 PyPI 安装测试
- [ ] PyPI 页面正确显示
- [ ] GitHub Release 已创建

### Docker 发布

- [ ] Docker 镜像已构建
- [ ] Docker Compose 测试通过
- [ ] Docker Hub 已推送（可选）

---

## 📦 项目文件清单

### 核心文件

```
nfo-to-vsmeta/
├── nfo_to_vsmeta_converter_complete.py  # 主程序
├── web_ui.py                            # Web UI
├── test_plugins.py                       # 插件测试
├── setup.py                              # 初始化脚本
├── quickstart.py                         # 快速启动
├── project_overview.py                   # 项目概览
│
├── requirements.txt                      # 依赖清单
├── pyproject.toml                        # 项目配置
├── MANIFEST.in                          # 打包清单
│
├── Dockerfile                            # Docker 镜像
├── docker-compose.yml                    # Docker Compose
├── .dockerignore                         # Docker 忽略
│
├── release.py                            # 发布脚本
├── RELEASE_GUIDE.md                     # 发布指南
├── DOCKER.md                             # Docker 指南
│
├── README.md                            # 项目文档
├── PROJECT_SUMMARY.md                   # 项目总结
├── PROJECT_STATUS.md                    # 项目状态
├── CHANGELOG.md                         # 更新日志
├── DEVELOPMENT.md                        # 开发指南
├── LICENSE                              # MIT 许可证
│
├── tests/                               # 测试目录
├── plugins/                             # 插件目录
├── docs/                                # 文档目录
└── .vscode/                             # VSCode 配置
```

---

## 🎯 使用场景

### 场景 1: Python 用户直接安装

```bash
pip install nfo-to-vsmeta
nfo-to-vsmeta -d ~/Movies
```

### 场景 2: Docker 用户

```bash
docker run -v ~/Movies:/data/movies nfo-to-vsmeta:latest
```

### 场景 3: 开发者

```bash
git clone https://github.com/example/nfo-to-vsmeta.git
cd nfo-to-vsmeta
python quickstart.py
```

### 场景 4: Web UI 用户

```bash
# Docker 方式
docker-compose up webui
# 访问 http://localhost:5000

# 或直接运行
pip install nfo-to-vsmeta[web]
nfo-vsmeta-web
```

---

## 📚 相关文档

- [README.md](README.md) - 完整使用指南
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目总结
- [DEVELOPMENT.md](DEVELOPMENT.md) - 开发指南
- [RELEASE_GUIDE.md](RELEASE_GUIDE.md) - PyPI 发布指南
- [DOCKER.md](DOCKER.md) - Docker 使用指南

---

## 🔗 链接

- **PyPI**: https://pypi.org/project/nfo-to-vsmeta/
- **Test PyPI**: https://test.pypi.org/project/nfo-to-vsmeta/
- **GitHub**: https://github.com/example/nfo-to-vsmeta
- **Docker Hub**: https://hub.docker.com/r/nfo-to-vsmeta

---

## 🤝 支持

- **文档**: 查看上述所有文档
- **Issue**: https://github.com/example/nfo-to-vsmeta/issues
- **Email**: support@example.com

---

**版本**: 2.0.1  
**更新**: 2026-05-17  
**状态**: ✅ 准备发布
