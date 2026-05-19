# Scripts directory

该目录包含辅助脚本，用于简化开发和发布流程。

## 📜 脚本列表

### bump_version.py
自动版本管理脚本，用于更新版本号和 CHANGELOG。

**使用方法：**
```bash
# 补丁版本升级 (1.2.3 → 1.2.4)
python scripts/bump_version.py patch

# 次版本升级 (1.2.3 → 1.3.0)
python scripts/bump_version.py minor

# 主版本升级 (1.2.3 → 2.0.0)
python scripts/bump_version.py major

# 试运行
python scripts/bump_version.py patch --dry-run
```

### release.sh
快速发布脚本，提供交互式的发布流程。

**使用方法：**
```bash
# 赋予执行权限
chmod +x scripts/release.sh

# 发布补丁版本
./scripts/release.sh patch

# 发布次版本
./scripts/release.sh minor
```

## 🚀 完整发布流程

```bash
# 1. 确保工作区干净
git status

# 2. 更新版本
./scripts/release.sh minor

# 3. 推送到 GitHub
git push && git push --tags

# 4. 等待 CI/CD 自动完成
# GitHub Actions 会自动处理剩余流程
```
