# 📝 PyPI 账户创建完整指南

## 目录

1. [简介](#简介)
2. [Test PyPI 账户创建](#test-pypi-账户创建)
3. [正式 PyPI 账户创建](#正式-pypi-账户创建)
4. [API Token 创建](#api-token-创建)
5. [配置 .pypirc 文件](#配置-pypirc-文件)
6. [验证账户](#验证账户)
7. [常见问题](#常见问题)

---

## 简介

本文档将指导你创建：
- ✅ Test PyPI 账户（测试发布）
- ✅ 正式 PyPI 账户（正式发布）
- ✅ API Token（安全认证）
- ✅ .pypirc 配置（本地使用）

---

## Test PyPI 账户创建

### 步骤 1: 访问 Test PyPI

打开浏览器访问：
```
https://test.pypi.org/
```

### 步骤 2: 注册账户

1. 点击右上角 **"Register"** 按钮
2. 填写注册表单：

| 字段 | 说明 |
|------|------|
| **Username** | 你的用户名（建议：类似 `nfo-to-vsmeta-author`） |
| **Email** | 有效的邮箱地址（用于验证） |
| **Password** | 强密码（至少 12 个字符） |
| **Confirm Password** | 再次输入密码 |

3. 点击 **"Register"** 按钮

### 步骤 3: 验证邮箱

1. 查看你的邮箱，会收到来自 Test PyPI 的验证邮件
2. 点击邮件中的 **"Verify your email address"** 链接
3. 验证成功后，你会看到确认页面

### 步骤 4: 登录 Test PyPI

1. 返回 `https://test.pypi.org/`
2. 点击右上角 **"Log in"**
3. 使用刚才创建的用户名和密码登录
4. 登录成功后，你会看到你的用户页面

✅ **Test PyPI 账户创建完成！**

---

## 正式 PyPI 账户创建

### 步骤 1: 访问正式 PyPI

打开浏览器访问：
```
https://pypi.org/
```

### 步骤 2: 注册账户

1. 点击右上角 **"Register"** 按钮
2. 填写注册表单（与 Test PyPI 类似）：

| 字段 | 说明 |
|------|------|
| **Username** | 你的正式用户名（建议：`your-name` 或 `your-org`） |
| **Email** | 正式的邮箱地址（用于验证和恢复） |
| **Password** | 强密码（至少 12 个字符） |
| **Confirm Password** | 再次输入密码 |

3. 点击 **"Register"** 按钮

### 步骤 3: 验证邮箱

1. 查看你的邮箱，会收到来自 PyPI 的验证邮件
2. 点击邮件中的 **"Verify your email address"** 链接
3. 验证成功后，你会看到确认页面

### 步骤 4: 登录正式 PyPI

1. 返回 `https://pypi.org/`
2. 点击右上角 **"Log in"**
3. 使用刚才创建的用户名和密码登录

✅ **正式 PyPI 账户创建完成！**

---

## API Token 创建（推荐）

使用 API Token 比直接使用密码更安全！

### Test PyPI API Token

1. 登录 Test PyPI
2. 点击右上角你的用户名 → **"Account settings"**
3. 滚动到 **"API tokens"** 部分
4. 点击 **"Add API token"**
5. 填写：

| 字段 | 建议值 |
|------|--------|
| **Token name** | `nfo-to-vsmeta-test` |
| **Scope** | Select **"Entire account"**（或者限定范围） |

6. 点击 **"Add token"** 按钮
7. **重要！** 复制生成的 Token！格式类似：
   ```
   pypi-AgEITlRlc3QABlBvc3VzZAACZAAAAAlwSFlzAAAWJQAA...
   ```
8. 保存 Token 到安全位置（只显示一次！）

### 正式 PyPI API Token

1. 登录正式 PyPI
2. 点击右上角你的用户名 → **"Account settings"**
3. 滚动到 **"API tokens"** 部分
4. 点击 **"Add API token"**
5. 填写：

| 字段 | 建议值 |
|------|--------|
| **Token name** | `nfo-to-vsmeta-release` |
| **Scope** | Select **"Entire account"** |

6. 点击 **"Add token"** 按钮
7. **重要！** 复制生成的 Token！
8. 保存 Token 到安全位置（只显示一次！）

✅ **API Token 创建完成！**

---

## 配置 .pypirc 文件

创建/编辑你的 `~/.pypirc` 文件：

### 方式 1: 使用 API Token（推荐）

在你的主目录创建/编辑 `~/.pypirc`：

**Linux/Mac**:
```bash
nano ~/.pypirc
```

**Windows** (PowerShell):
```powershell
notepad $env:USERPROFILE\.pypirc
```

**内容**：
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEITlRlc3QABlBvc3VzZAACZAAAAAlwSFlzAAAWJQAA...（你的正式 PyPI Token）

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEITlRlc3QABlBvc3VzZAACZAAAAAlwSFlzAAAWJQAA...（你的 Test PyPI Token）
```

### 方式 2: 使用密码（不推荐，不安全）

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = your-username
password = your-password

[testpypi]
repository = https://test.pypi.org/legacy/
username = your-username
password = your-password
```

### 权限设置（Linux/Mac）

```bash
chmod 600 ~/.pypirc
```

✅ **.pypirc 配置完成！**

---

## 验证账户

### 验证 Test PyPI

运行发布脚本来测试：

```bash
# 切换到项目目录
cd /workspace

# 清理构建目录
python release.py clean

# 测试上传到 Test PyPI
python release.py testpypi
```

### 验证正式 PyPI（谨慎！）

**注意：** 先在 Test PyPI 测试成功后，再进行正式发布！

```bash
# 上传到正式 PyPI
python release.py pypi
```

---

## 常见问题

### Q1: 邮箱收不到验证邮件？

**A**:
- 检查垃圾邮件/垃圾箱
- 添加 `noreply@pypi.org` 到白名单
- 稍后重试

### Q2: 用户名已被占用？

**A**:
- 尝试不同的变体（添加后缀如 `-author`）
- 联系 PyPI 支持（如果是你的商标）

### Q3: 可以用同一个邮箱创建两个账户？

**A**:
- 可以！Test PyPI 和正式 PyPI 是独立的

### Q4: Token 泄露了怎么办？

**A**:
1. 立即到 PyPI 账户设置删除该 Token
2. 创建新的 Token
3. 更新 `~/.pypirc` 文件

### Q5: 2FA（双因素认证）是什么？

**A**:
- 强烈建议启用！
- 在 Account settings 中设置
- 支持 Authy、Google Authenticator、手机短信等方式

---

## 下一步

### 账户创建完成后，你可以：

1. ✅ 运行 `python release.py full` 测试完整流程
2. ✅ 测试 Test PyPI 发布
3. ✅ 正式发布到 PyPI
4. ✅ 创建 Docker 镜像
5. ✅ 发布到 GitHub

---

## 快速链接

- **Test PyPI**: https://test.pypi.org/
- **正式 PyPI**: https://pypi.org/
- **PyPI 帮助文档**: https://pypi.org/help/
- **打包指南**: https://packaging.python.org/

---

**文档版本**: 1.0  
**最后更新**: 2026-05-17  
**项目**: NFO to VSMETA Converter v2.0.1
