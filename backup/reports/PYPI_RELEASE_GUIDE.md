# PyPI 正式发布指南

本指南说明如何配置 GitHub Secrets 中的 PyPI 令牌并实现正式版本的自动发布。

## 目录

- [1. 获取 PyPI API 令牌](#1-获取-pypi-api-令牌)
- [2. 配置 GitHub Secrets](#2-配置-github-secrets)
- [3. 自动发布流程](#3-自动发布流程)
- [4. 手动发布](#4-手动发布)
- [5. 验证发布](#5-验证发布)

---

## 1. 获取 PyPI API 令牌

### 步骤 1：登录 PyPI

访问 [PyPI 官网](https://pypi.org/) 并登录您的账户。

### 步骤 2：创建 API 令牌

1. 点击右上角您的用户名，选择 **Account settings**
2. 在 **API tokens** 部分，点击 **Add API token**
3. 填写以下信息：
   - **Token name**: `GitHub Actions CI/CD`（或其他描述性名称）
   - **Scope**: 选择 **Entire account**（或仅针对特定项目）
4. 点击 **Add token**
5. **重要**：立即复制生成的令牌（格式类似 `pypi-xxxxx...`），只显示一次！

## 2. 配置 GitHub Secrets

### 步骤 1：访问仓库设置

1. 打开您的 GitHub 仓库
2. 点击 **Settings** 标签页
3. 在左侧菜单中选择 **Secrets and variables** > **Actions**

### 步骤 2：添加 PyPI API 令牌

1. 点击 **New repository secret**
2. **Name**: `PYPI_API_TOKEN`
3. **Secret**: 粘贴您在第 1 步获取的 PyPI API 令牌
4. 点击 **Add secret**

### 验证 Secrets 配置

确认您的仓库有以下 Secrets：
- `PYPI_API_TOKEN` - PyPI 正式发布令牌（刚刚添加）
- `TEST_PYPI_API_TOKEN` - Test PyPI 令牌（之前已配置）

## 3. 自动发布流程

### 发布条件

正式 PyPI 发布仅在以下情况下触发：
- 推送以 `v` 开头的标签时（如 `v1.0.0`、`v2.0.1`）
- 所有测试通过
- 构建成功

### 创建并推送标签

```bash
# 确保在 main 分支上
git checkout main
git pull origin main

# 创建并推送标签
git tag -a v2.0.2 -m "Release version 2.0.2"
git push origin v2.0.2
```

### 标签命名规范

遵循语义化版本（Semantic Versioning）：
- `vMAJOR.MINOR.PATCH`
- 示例：`v1.0.0`, `v1.1.0`, `v2.0.1`

## 4. 手动发布

如果需要手动发布，按以下步骤操作：

### 步骤 1：安装发布工具

```bash
pip install --upgrade build twine
```

### 步骤 2：构建包

```bash
python -m build --sdist --wheel --outdir dist/
```

### 步骤 3：检查包

```bash
twine check dist/*
```

### 步骤 4：发布到 PyPI

```bash
twine upload dist/*
```

或者使用 API 令牌：
```bash
twine upload dist/* -u __token__ -p pypi-xxxxx...
```

## 5. 验证发布

### 检查 PyPI 页面

访问您的项目页面：
https://pypi.org/p/nfo-to-vsmeta

### 测试安装

```bash
# 创建新的虚拟环境
python -m venv test-env
source test-env/bin/activate  # Linux/Mac
# 或 test-env\Scripts\activate  # Windows

# 安装包
pip install nfo-to-vsmeta

# 验证安装
python -c "import nfo_to_vsmeta_converter_complete; print('安装成功！')"
```

## CI/CD 配置说明

已更新的 [`.github/workflows/ci.yml`](.github/workflows/ci.yml) 包含：

### `deploy-pypi` Job 配置

```yaml
deploy-pypi:
  name: Deploy to PyPI
  runs-on: ubuntu-latest
  needs: build
  if: startsWith(github.ref, 'refs/tags/v')  # 仅在 v 开头标签时触发
  environment:
    name: pypi
    url: https://pypi.org/p/nfo-to-vsmeta
  permissions:
    id-token: write  # OIDC 认证所需权限

  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Download artifacts
      uses: actions/download-artifact@v4
      with:
        name: dist
        path: dist/
    - name: Publish distribution to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

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

# 5. 监控 GitHub Actions 执行
# 访问仓库的 Actions 标签页查看进度
```

## 回滚发布

如果需要从 PyPI 删除版本：

1. 访问 https://pypi.org/manage/project/nfo-to-vsmeta/releases/
2. 找到要删除的版本
3. 点击 **Options** > **Delete**
4. 确认删除

**注意**：PyPI 不允许重新上传相同版本号的包，删除后需要升级版本号。

## 安全最佳实践

1. **不要将 API 令牌提交到代码仓库**
2. 令牌权限范围按需最小化
3. 定期轮换 API 令牌
4. 使用 GitHub Secrets 管理敏感信息
5. 限制仓库的写入权限

## 故障排除

### 发布失败

1. 检查 GitHub Actions 日志
2. 确认 `PYPI_API_TOKEN` 已正确配置
3. 确认包版本号在 PyPI 上不存在
4. 确认包名称正确

### 测试失败阻止发布

这是正常行为！CI/CD 会确保只有通过所有测试的代码才能发布。

---

如有问题，请查看：
- [PyPI 帮助文档](https://pypi.org/help/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
