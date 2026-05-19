# 开发指南

欢迎参与 NFO to VSMETA 转换器的开发！本指南将帮助你设置开发环境并开始贡献代码。

## 📋 目录

- [环境设置](#环境设置)
- [代码风格](#代码风格)
- [运行测试](#运行测试)
- [提交代码](#提交代码)
- [调试技巧](#调试技巧)

---

## 🔧 环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/nfo-to-vsmeta.git
cd nfo-to-vsmeta
```

### 2. 运行初始化脚本

```bash
python setup.py
```

这将:
- 创建虚拟环境
- 安装依赖
- 初始化 Git（如果需要）
- 创建必要的目录

### 3. 激活虚拟环境

**Linux/Mac:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

### 4. 安装开发依赖

```bash
pip install black mypy flake8 pytest
```

---

## 🎨 代码风格

我们使用以下工具来保持代码质量:

### 格式化工具

```bash
# 使用 black 格式化
black .

# 指定文件
black nfo_to_vsmeta_converter_complete.py
```

### 类型检查

```bash
# 运行 mypy
mypy nfo_to_vsmeta_converter_complete.py
```

### 代码检查

```bash
# 运行 flake8
flake8 nfo_to_vsmeta_converter_complete.py
```

### 编辑器配置

如果你使用 VSCode，我们已经提供了 `.vscode/settings.json`，它将自动:
- 保存时格式化
- 显示类型检查错误
- 显示 linting 警告

---

## 🧪 运行测试

### 快速测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行插件系统测试
pytest tests/test_plugin_system.py -v

# 运行配置测试
pytest tests/test_config.py -v
```

### 覆盖率报告

```bash
pip install pytest-cov
pytest tests/ --cov=nfo_to_vsmeta_converter_complete --cov-report=html
# 然后打开 htmlcov/index.html
```

### 插件系统测试

```bash
# 运行专用的插件测试脚本
python test_plugins.py
```

---

## 📝 开发工作流

### 1. 创建新功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 编写代码

- 确保遵循代码风格
- 添加必要的类型提示
- 编写或更新文档

### 3. 运行测试

```bash
pytest tests/
```

### 4. 格式化和检查

```bash
black .
mypy nfo_to_vsmeta_converter_complete.py
flake8 nfo_to_vsmeta_converter_complete.py
```

### 5. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能描述"
git push
```

---

## 🔍 调试技巧

### 打印调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告")
logger.error("错误")
```

### 使用 pdb

```python
import pdb; pdb.set_trace()
```

### 在 IDE 中调试

对于 VSCode，创建 `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: 主程序",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/nfo_to_vsmeta_converter_complete.py",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Web UI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/web_ui.py",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: 测试",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/.venv/bin/pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

---

## 📚 资源

### 相关文档

- [README.md](README.md) - 项目主文档
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目总结
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - 项目状态
- [CHANGELOG.md](CHANGELOG.md) - 更新日志

### 插件开发

- [docs/plugin-system-optimization-design.md](docs/plugin-system-optimization-design.md) - 插件系统设计
- [docs/plugin-system-optimization-plan.md](docs/plugin-system-optimization-plan.md) - 插件系统优化计划
- [plugins/demo_metadata_enhancer/](plugins/demo_metadata_enhancer/) - 示例插件

### 示例文件

查看现有代码:
- [nfo_to_vsmeta_converter_complete.py](nfo_to_vsmeta_converter_complete.py) - 主程序
- [tests/test_plugin_system.py](tests/test_plugin_system.py) - 测试示例

---

## 🐛 报告问题

如果你发现了 bug 或有功能建议:

1. 检查现有 issue 是否已经存在
2. 创建新 issue，包含:
   - 详细描述
   - 复现步骤
   - 预期行为
   - 实际行为
   - 环境信息（Python 版本、操作系统）
   - 日志或截图（如果适用）

---

## 🎉 贡献指南

我们欢迎任何形式的贡献！

### 贡献类型

- Bug 修复
- 新功能
- 文档改进
- 测试完善
- 示例插件

### 提交 Pull Request

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

---

## 📖 学习资源

### Python

- [Python 官方文档](https://docs.python.org/3/)
- [Python 类型提示](https://docs.python.org/3/library/typing.html)

### 测试

- [pytest 文档](https://docs.pytest.org/)

### 工具

- [black](https://black.readthedocs.io/) - 代码格式化
- [mypy](https://mypy.readthedocs.io/) - 类型检查
- [flake8](https://flake8.pycqa.org/) - 代码检查

---

**祝你开发愉快！🚀**
