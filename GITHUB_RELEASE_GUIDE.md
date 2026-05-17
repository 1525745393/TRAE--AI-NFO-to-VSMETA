# GitHub Release 创建指南

## 📋 已完成

- ✅ Git 标签已创建并推送: `v2.0.1`
- ✅ 发布包已构建:
  - `nfo_to_vsmeta-2.0.1.tar.gz` (155.0 KB)
  - `nfo_to_vsmeta-2.0.1-py3-none-any.whl` (78.2 KB)

---

## 🚀 在 GitHub 网站上创建 Release

### 步骤 1: 访问 Releases 页面

1. 打开浏览器，访问: https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA
2. 点击右侧栏中的 **"Releases"** 链接
3. 点击 **"Draft a new release"** 按钮

### 步骤 2: 选择标签

1. 在 **"Choose a tag"** 下拉菜单中
2. 选择 `v2.0.1` (已推送的标签)
3. **Target** 保持为 `main`

### 步骤 3: 填写发布信息

**Release title:**
```
v2.0.1 - 插件系统优化
```

**Describe this release:**
```markdown
## 🎉 新功能

- **插件系统优化**
  - ✅ 实现插件依赖管理和拓扑排序
  - ✅ 实现插件优先级控制系统（0-100）
  - ✅ 实现插件配置持久化（PluginConfig）
  - ✅ 实现插件热重载功能（watchdog）
  - ✅ 实现插件模板生成器

## ✨ 改进

- 优化插件加载流程
- 改进插件注册机制
- 增强错误处理和日志记录
- Web UI 插件管理界面增强

## 🐛 修复

- 修复插件优先级排序问题
- 修复配置文件加载问题

---

## 📦 安装方式

### PyPI (推荐)
```bash
pip install nfo-to-vsmeta[all]
```

### 从源码安装
```bash
pip install nfo_to_vsmeta-2.0.1-py3-none-any.whl
```

---

**完整更新日志**: [CHANGELOG.md](https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA/blob/main/CHANGELOG.md)
```

### 步骤 4: 上传构建产物

1. 在 **"Attach binaries by dropping them here or selecting them."** 区域
2. 点击 **"Attach binaries"**
3. 选择以下文件:
   - `dist/nfo_to_vsmeta-2.0.1.tar.gz`
   - `dist/nfo_to_vsmeta-2.0.1-py3-none-any.whl`

### 步骤 5: 发布

1. 确认 **"Set as the latest release"** 已勾选
2. 点击 **"Publish release"** 按钮

---

## 📝 Release 信息速查

| 项目 | 值 |
|------|-----|
| **版本** | v2.0.1 |
| **发布日期** | 2024-12-17 |
| **PyPI 包名** | nfo-to-vsmeta |
| **GitHub 仓库** | https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA |
| **标签** | v2.0.1 |
| **分支** | main |

---

## 🎯 完成后验证

发布完成后，请确认:

- [ ] Release 页面显示正常
- [ ] 构建产物已正确上传
- [ ] 可以访问 https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA/releases/tag/v2.0.1
- [ ] PyPI 包可以正常安装: `pip install nfo-to-vsmeta[all]`
