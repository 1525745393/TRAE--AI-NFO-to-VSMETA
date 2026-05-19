# PyPI 发布指南

本指南将帮助你将 NFO to VSMETA 转换器发布到 PyPI（Python Package Index）。

## 📋 目录

- [准备工作](#准备工作)
- [发布到 Test PyPI](#发布到-test-pypi)
- [发布到正式 PyPI](#发布到-正式-pypi)
- [使用发布脚本](#使用发布脚本)
- [常见问题](#常见问题)

---

## 🔧 准备工作

### 1. 安装构建工具

```bash
pip install --upgrade build twine
```

### 2. 创建 PyPI 账户

#### Test PyPI
1. 访问 https://test.pypi.org/account/register/
2. 创建账户并验证邮箱

#### 正式 PyPI
1. 访问 https://pypi.org/account/register/
2. 创建账户并验证邮箱
3. 设置双因素认证（推荐）

### 3. 配置 PyPI 凭证

创建 `~/.pypirc` 文件：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = your_username
password = your_password

[testpypi]
repository = https://test.pypi.org/legacy/
username = your_username
password = your_password
```

或者使用令牌认证（更安全）：

```ini
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. 准备项目

确保项目满足以下要求：

- ✅ `pyproject.toml` 已配置完整
- ✅ `README.md` 存在且格式正确
- ✅ `LICENSE` 文件存在
- ✅ `MANIFEST.in` 已创建
- ✅ 所有测试通过
- ✅ 版本号已更新

---

## 🚀 发布到 Test PyPI

Test PyPI 允许你在不影响正式环境的情况下测试发布流程。

### 方法 1: 使用命令行

```bash
# 1. 清理构建目录
rm -rf build/ dist/ *.egg-info

# 2. 构建包
python -m build

# 3. 上传到 Test PyPI
python -m twine upload --repository testpypi dist/*
```

### 方法 2: 使用发布脚本

```bash
python release.py testpypi
```

### 4. 验证发布

安装 Test PyPI 的包进行测试：

```bash
# 创建虚拟环境
python -m venv test-env
source test-env/bin/activate  # Linux/Mac
# test-env\Scripts\activate  # Windows

# 从 Test PyPI 安装
pip install --index-url https://test.pypi.org/simple/ nfo-to-vsmeta

# 测试安装
nfo-to-vsmeta --help

# 测试 Web UI
nfo-vsmeta-web

# 清理
deactivate
rm -rf test-env
```

---

## 📦 发布到正式 PyPI

在 Test PyPI 测试通过后，可以发布到正式 PyPI。

### 方法 1: 使用命令行

```bash
# 1. 清理构建目录
rm -rf build/ dist/ *.egg-info

# 2. 构建包
python -m build

# 3. 上传到正式 PyPI
python -m twine upload dist/*
```

### 方法 2: 使用发布脚本

```bash
python release.py pypi
```

### 3. 验证发布

安装正式版本的包：

```bash
# 安装
pip install nfo-to-vsmeta

# 测试
nfo-to-vsmeta --help
nfo-vsmeta-web
```

访问 https://pypi.org/project/nfo-to-vsmeta/ 查看发布页面。

---

## 🎯 使用发布脚本

我们创建了一个完整的发布脚本 `release.py`。

### 基本用法

```bash
# 查看帮助
python release.py --help

# 清理构建目录
python release.py clean

# 运行测试
python release.py test

# 检查代码质量
python release.py quality

# 构建包
python release.py build

# 上传到 Test PyPI
python release.py testpypi

# 上传到正式 PyPI
python release.py pypi

# 创建 Git 标签
python release.py tag

# 完整发布流程
python release.py full
```

### 完整发布流程

```bash
# 1. 完整发布（不包括上传）
python release.py full

# 2. 测试安装
pip install dist/*.whl --force-reinstall

# 3. 上传到 Test PyPI
python release.py testpypi

# 4. 测试安装
pip install --index-url https://test.pypi.org/simple/ nfo-to-vsmeta

# 5. 上传到正式 PyPI
python release.py pypi

# 6. 创建 Git 标签
python release.py tag
```

---

## 📝 版本管理

### 语义化版本

本项目使用语义化版本（SemVer）：

```
主版本.次版本.修订版本

例如：2.0.1
  主版本：2 - 重大功能更新
  次版本：0 - 新功能（向后兼容）
  修订版本：1 - Bug 修复
```

### 更新版本号

在 `pyproject.toml` 中更新版本：

```toml
[project]
name = "nfo-to-vsmeta"
version = "2.0.1"  # 更新这里
```

或在代码中定义版本（如果适用）。

### Git 标签

```bash
# 创建标签
git tag -a v2.0.1 -m "Release version 2.0.1"

# 推送标签
git push origin v2.0.1
```

---

## ⚠️ 常见问题

### Q1: 上传失败 "File already exists"

如果你重新上传相同版本：

```
HTTPError: 400 Client Error: File already exists
```

解决：更新版本号后重新构建和上传。

### Q2: 认证失败

检查 `~/.pypirc` 配置或使用令牌认证：

```bash
# 使用令牌上传
twine upload --username __token__ --password pypi-xxx dist/*
```

### Q3: 构建失败

```bash
# 确保使用最新版本的构建工具
pip install --upgrade build twine setuptools wheel

# 清理后重新构建
rm -rf build/ dist/ *.egg-info
python -m build
```

### Q4: 测试安装失败

检查依赖是否正确配置在 `pyproject.toml` 中。

### Q5: 包名冲突

如果 `nfo-to-vsmeta` 已被占用，你需要选择一个新名称。

---

## 🔄 自动化发布

### GitHub Actions

创建 `.github/workflows/release.yml`：

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine
          
      - name: Build package
        run: python -m build
        
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
```

在 GitHub 仓库设置中添加 `PYPI_TOKEN` secret。

---

## ✅ 发布检查清单

在正式发布前，确保以下项目都已完成：

### 代码检查
- [ ] 所有代码已完成
- [ ] 所有测试通过
- [ ] 代码已格式化（black）
- [ ] 类型检查通过（mypy）
- [ ] Lint 检查通过（flake8）

### 文档检查
- [ ] README.md 已更新
- [ ] CHANGELOG.md 已更新
- [ ] LICENSE 文件正确
- [ ] pyproject.toml 完整

### 版本管理
- [ ] 版本号已更新
- [ ] Git 提交已完成
- [ ] Git 标签已创建

### PyPI 配置
- [ ] PyPI 账户已创建
- [ ] 双因素认证已启用
- [ ] API Token 已生成
- [ ] .pypirc 已配置

### 测试检查
- [ ] Test PyPI 测试通过
- [ ] 正式安装测试通过
- [ ] 功能测试通过

### 发布后
- [ ] PyPI 页面正确显示
- [ ] 安装说明正确
- [ ] GitHub Release 已创建
- [ ] 发布公告已发送

---

## 🎉 恭喜

如果一切顺利，你的包现在已经在 PyPI 上了！

查看你的项目页面：https://pypi.org/project/nfo-to-vsmeta/

用户现在可以使用以下命令安装你的包：

```bash
pip install nfo-to-vsmeta
```

---

## 📚 相关资源

- [PyPI 官方文档](https://packaging.python.org/)
- [Python 打包用户指南](https://packaging.python.org/tutorials/packaging-projects/)
- [Test PyPI 使用指南](https://packaging.python.org/guides/using-testpypi/)
- [twine 文档](https://twine.readthedocs.io/)

---

**祝你发布顺利！🎊**
