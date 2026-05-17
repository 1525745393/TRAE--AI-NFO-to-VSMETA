# NFO to VSMETA 转换器

<div align="center">

[![版本](https://img.shields.io/badge/version-2.0.1-blue.svg)](https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![许可](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

**将 Kodi/XBMC 格式的 NFO 元数据文件转换为群晖 Video Station 的 VSMETA 格式**

</div>

## 📋 目录

- [功能特性](#-功能特性)
- [安装](#-安装)
- [快速开始](#-快速开始)
- [使用文档](#-使用文档)
- [插件系统](#-插件系统)
- [配置选项](#-配置选项)
- [Web UI](#-web-ui)
- [开发](#-开发)
- [常见问题](#-常见问题)

---

## ✨ 功能特性

### 核心功能
- 🎬 **NFO 解析** - 支持 Kodi/XBMC 标准 XML 格式，自动提取影片元数据
- 📝 **VSMETA 生成** - 生成群晖 Video Station 兼容的二进制元数据文件
- ⚡ **并发处理** - 支持多线程/多进程模式，充分利用多核 CPU
- 💾 **断点续传** - 支持中断后继续处理，避免重复工作
- 🔄 **智能重试** - 失败文件自动重试，支持配置重试次数和延迟
- 🖼️ **图片压缩** - 自动压缩海报图片，支持配置大小和压缩比
- 📦 **图片缓存** - LRU 缓存机制，避免重复压缩相同图片

### 用户体验
- 📊 **进度显示** - tqdm 进度条实时显示处理进度
- 🎨 **彩色输出** - 彩色终端输出，提升用户体验
- ⌨️ **交互菜单** - 支持上下键导航的友好菜单界面
- 🔒 **信号处理** - 支持 Ctrl+C 优雅退出，自动保存进度
- 📄 **报告导出** - 支持 HTML/CSV/TXT 三种格式的转换报告

### 扩展功能
- 🔌 **插件系统** - 强大的插件架构，支持自定义扩展
- 🤖 **智能助手** - 自然语言配置输入，智能推荐参数
- 🧠 **AI 补全** - 利用 AI 补全缺失的影片信息（预留）
- 🌡️ **热重载** - 插件修改无需重启，立即生效

---

## 📥 安装

### 环境要求

- Python 3.8 或更高版本
- 群晖 Synology NAS（用于运行转换后的 VSMETA 文件）

### 安装步骤

1. **克隆或下载项目**
```bash
git clone https://github.com/1525745393/TRAE--AI-NFO-to-VSMETA.git
cd nfo-to-vsmeta
```

2. **创建虚拟环境（推荐）**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
# 安装所有依赖
pip install -r requirements.txt

# 或仅安装必需依赖（可选功能将不可用）
pip install Pillow tqdm colorama readchar watchdog Flask
```

### 依赖说明

| 依赖 | 必需 | 功能 |
|------|------|------|
| Pillow | ❌ | 海报图片压缩 |
| tqdm | ❌ | 进度条显示 |
| colorama | ❌ | 彩色终端输出 |
| readchar | ❌ | 交互式菜单 |
| watchdog | ❌ | 插件热重载 |
| Flask | ❌ | Web UI 界面 |

---

## 🚀 快速开始

### 命令行模式

处理单个目录：
```bash
python nfo_to_vsmeta_converter_complete.py -d /path/to/movies --workers 8
```

处理多个目录：
```bash
python nfo_to_vsmeta_converter_complete.py -d /path/movies /path/series --workers 4
```

### 交互模式

启动后选择功能菜单：
```bash
python nfo_to_vsmeta_converter_complete.py -i
```

### Web UI 模式

启动 Web 管理界面：
```bash
python web_ui.py
# 访问 http://localhost:5000
```

---

## 📖 使用文档

### 基本用法

#### 1. 准备 NFO 文件

确保你的影片目录下有对应的 `.nfo` 文件。NFO 文件应该与视频文件同名：

```
Movies/
├── Movie1/
│   ├── Movie1.mp4
│   └── Movie1.nfo
└── Movie2/
    ├── Movie2.mkv
    ├── Movie2-poster.jpg  # 可选的海报
    └── Movie2.nfo
```

#### 2. 运行转换

```bash
# 基本用法
python nfo_to_vsmeta_converter_complete.py -d /path/to/movies

# 指定线程数
python nfo_to_vsmeta_converter_complete.py -d /path/to/movies --workers 8

# 覆盖已有文件
python nfo_to_vsmeta_converter_complete.py -d /path/to/movies --overwrite

# 仅生成报告（不实际转换）
python nfo_to_vsmeta_converter_complete.py -d /path/to/movies --dry-run
```

#### 3. 查看报告

转换完成后会自动生成报告文件：
- `conversion_report.html` - HTML 格式（可在浏览器中查看）
- `conversion_report.csv` - CSV 格式（可用 Excel 打开）
- `conversion_report.txt` - 文本格式

---

## 🔌 插件系统

### 插件架构

插件系统支持 5 种类型的扩展：

| 插件类型 | 描述 | 方法 |
|---------|------|------|
| **NFOParserPlugin** | NFO 解析 | `parse(nfo_path, metadata)` |
| **VSMETAGeneratorPlugin** | VSMETA 生成 | `generate(metadata, vsmeta_data)` |
| **MetadataEnhancerPlugin** | 元数据增强 | `enhance(metadata, filepath)` |
| **FileFilterPlugin** | 文件过滤 | `should_process(filepath, filename)` |
| **LifecyclePlugin** | 生命周期钩子 | `on_start()`, `on_file_start()`, `on_file_end()`, `on_finish()` |

### 安装插件

#### 方法 1: 复制插件文件

```bash
# 将插件复制到 plugins 目录
cp my_plugin.py plugins/
```

#### 方法 2: 使用模板创建插件

```bash
# 创建元数据增强插件
python nfo_to_vsmeta_converter_complete.py --create-plugin my_enhancer \
    --plugin-type enhancer \
    --plugin-author "Your Name" \
    --plugin-description "我的增强插件"

# 创建文件过滤插件
python nfo_to_vsmeta_converter_complete.py --create-plugin my_filter \
    --plugin-type filter
```

### 插件配置

每个插件可以有自己的配置文件：

```
plugins/
├── configs/
│   ├── my_plugin.json
│   └── another_plugin.json
├── my_plugin.py
└── another_plugin.py
```

#### 插件优先级

插件支持优先级控制（0-100），数字越大优先级越高：

```python
@property
def priority(self) -> int:
    return 75  # 高优先级
```

或使用装饰器：

```python
@plugin_priority(80)
class HighPriorityPlugin(Plugin):
    pass
```

#### 插件依赖

插件可以声明依赖关系：

```python
@property
def dependencies(self) -> list:
    return ['base_plugin']  # 必须依赖

@property
def optional_dependencies(self) -> list:
    return ['optional_helper']  # 可选依赖
```

### 热重载

启用热重载后，修改插件文件无需重启：

```python
from nfo_to_vsmeta_converter_complete import PluginManager

pm = PluginManager()
pm.enable_hot_reload('plugins', config)
```

或在 Web UI 中启用"热重载"开关。

---

## ⚙️ 配置选项

### 命令行参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `-d, --directory` | 处理目录（可指定多个） | 当前目录 |
| `--workers` | 并发工作线程数 | 4 |
| `--overwrite` | 覆盖已有 VSMETA | False |
| `--dry-run` | 预演模式（不实际写入） | False |
| `--log-level` | 日志级别 | INFO |

### 配置文件

创建 `config.json` 来自定义配置：

```json
{
  "directory": ["/path/to/movies"],
  "max_workers": 8,
  "max_image_size_kb": 200,
  "image_compression_ratio": 0.8,
  "retry_attempts": 3,
  "retry_delay": 1.0,
  "process_mode": "thread",
  "enable_backup": true,
  "overwrite_existing": false
}
```

### 详细配置项

#### 文件过滤
```json
{
  "file_include_patterns": ["*.mp4", "*.mkv"],
  "file_exclude_patterns": ["*.sample*"],
  "file_regex": ".*1080p.*",
  "min_size": 1048576,
  "max_size": 10737418240
}
```

#### 图片设置
```json
{
  "max_image_size_kb": 200,
  "image_compression_ratio": 0.8,
  "image_cache_max_size": 50
}
```

#### 性能优化
```json
{
  "max_workers": 8,
  "process_mode": "thread",
  "checkpoint_save_interval": 10
}
```

---

## 🌐 Web UI

### 启动

```bash
python web_ui.py
# 默认访问 http://localhost:5000
```

### 功能页面

- **📊 仪表盘** - 实时状态概览、进度显示
- **⚙️ 配置** - 可视化编辑所有配置项
- **🤖 智能助手** - 自然语言配置输入
- **🚀 转换** - 启动/停止转换、查看扫描结果
- **🧰 工具箱** - NFO 验证、VSMETA 预览
- **📄 报告** - 转换报告、性能分析
- **💾 断点** - 断点续传管理
- **📦 备份** - 备份文件管理
- **🔌 插件** - 插件管理、配置、热重载

### 快捷键

- `Ctrl+S` - 保存配置
- `Ctrl+R` - 刷新状态
- `Ctrl+Enter` - 开始转换
- `ESC` - 关闭弹窗
- `1-9` - 切换标签页
- `T` - 切换主题

---

## 👨‍💻 开发

### 项目结构

```
nfo-to-vsmeta/
├── nfo_to_vsmeta_converter_complete.py  # 主程序
├── web_ui.py                             # Web UI
├── single_file_converter_optimized_fixed.py  # 简化版
├── test_plugins.py                       # 插件测试
├── requirements.txt                      # 依赖文件
├── plugins/                              # 插件目录
│   ├── configs/                          # 插件配置
│   ├── demo_metadata_enhancer/           # 示例插件
│   ├── file_size_filter.py
│   └── metadata_logger.py
└── docs/                                 # 文档
    ├── plugin-system-optimization-design.md
    └── plugin-system-optimization-plan.md
```

### 开发插件

参考 `plugins/demo_metadata_enhancer/` 目录中的示例。

### 运行测试

```bash
# 测试插件系统
python test_plugins.py

# 测试主程序
python nfo_to_vsmeta_converter_complete.py -d /path/to/test --dry-run
```

---

## ❓ 常见问题

### Q: 转换失败怎么办？

1. 检查 NFO 文件格式是否正确
2. 使用 `--log-level DEBUG` 查看详细日志
3. 查看转换报告中的错误详情
4. 使用智能重试功能

### Q: 如何处理大量文件？

1. 增加 `--workers` 参数使用更多线程
2. 使用 `--process-mode process` 启用多进程
3. 确保内存充足

### Q: 插件不生效？

1. 确认插件文件在 `plugins/` 目录中
2. 检查插件是否正确继承基类
3. 查看日志中的插件加载信息
4. 尝试启用热重载

### Q: 海报图片模糊？

1. 增大 `max_image_size_kb` 配置
2. 调高 `image_compression_ratio`（接近 1.0）
3. 使用更高分辨率的原始海报

### Q: 如何获取帮助？

- 查看详细文档：`docs/`
- 运行帮助：`python nfo_to_vsmeta_converter_complete.py --help`
- 查看示例：`plugins/demo_metadata_enhancer/`

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- 使用 [Pillow](https://pillow.readthedocs.io/) 处理图片
- 使用 [tqdm](https://tqdm.github.io/) 显示进度条
- 使用 [watchdog](https://pythonhosted.org/watchdog/) 实现热重载
- 使用 [Flask](https://flask.palletsprojects.com/) 构建 Web UI

---

<div align="center">

**如果这个项目对你有帮助，请给我们一个 ⭐！**

</div>
