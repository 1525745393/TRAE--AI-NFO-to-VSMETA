# 配置管理系统使用文档

## 概述

这是一个完善的集中式配置管理系统，提供以下功能：

- 📦 配置统一管理
- 💾 配置持久化（JSON 格式）
- 🔧 配置自动验证
- 📋 配置变更监听
- 🗂️ 自动备份机制
- 🌐 跨平台支持

## 快速开始

### 基本用法

```python
from config import ConfigManager, get_config_manager

# 获取单例配置管理器
mgr = get_config_manager()

# 访问配置
print(mgr.config.converter.max_workers)
print(mgr.config.ui.theme)

# 修改配置
mgr.config.converter.max_workers = 8
mgr.save()

# 便捷方法获取和设置
value = mgr.get_value("converter.max_workers")
mgr.set_value("ui.theme", "light")
```

### 使用独立实例（不推荐用于单例模式测试）

```python
from config import ConfigManager

# 使用自定义配置目录
mgr = ConfigManager(config_dir="/path/to/config")

# 配置会自动保存到指定目录
```

## 配置结构

### ConfigSchema（完整配置）

包含所有配置分类：

```python
{
  "version": "1.0",
  "converter": ConverterConfig,
  "ui": UIConfig,
  "plugins": PluginConfig,
  "cache": CacheConfig,
  "logging": LoggingConfig
}
```

### ConverterConfig（转换器配置）

```python
from config import ConverterConfig

config = ConverterConfig(
    directories=["/path/to/videos"],
    max_workers=4,
    max_image_size_kb=200,
    image_compression_ratio=0.8,
    auto_backup=True,
    skip_existing=True
)
```

### UIConfig（界面配置）

```python
from config import UIConfig, ThemeMode

config = UIConfig(
    theme=ThemeMode.DARK,
    auto_scroll=True,
    window_width=1280,
    window_height=800
)

# 添加最近使用目录
config.add_recent_directory("/path/used/recently")
```

### 其他配置类

- `PluginConfig` - 插件管理配置
- `CacheConfig` - 缓存配置
- `LoggingConfig` - 日志配置

## 高级功能

### 配置变更监听

```python
from config import get_config_manager, ConfigSchema

mgr = get_config_manager()

def on_config_change(config: ConfigSchema):
    print(f"配置已更新！主题：{config.ui.theme}")

mgr.on_change("my_listener", on_config_change)

# 配置保存后会自动调用监听函数
mgr.config.ui.theme = "ocean"
mgr.save()
```

### 导出配置 Schema

```python
schema = mgr.export_schema()

# 可以用于构建 UI 配置界面
print(schema["converter"]["max_workers"]["label"])
print(schema["converter"]["max_workers"]["min"])
print(schema["converter"]["max_workers"]["max"])
```

### 重置为默认配置

```python
mgr.reset_to_default()
mgr.save()
```

### 管理备份文件

```python
# 获取所有配置文件（包括备份）
all_files = mgr.get_all_config_files()

# 备份会自动创建，保留最近 10 个版本
```

## 配置目录位置

配置会自动保存到以下位置：

| 系统 | 路径 |
|------|------|
| Windows | `%LOCALAPPDATA%\NfoToVsmeta\config.json` |
| Linux/macOS | `~/.config/nfo_to_vsmeta/config.json` |

可以通过环境变量 `NFO_VSMETA_CONFIG_DIR` 自定义配置目录。

## 示例配置文件

参考 `config/config.example.json` 查看完整的配置示例。

## 测试

运行配置管理系统测试：

```bash
pytest tests/test_config_manager.py -v
```

## API 参考

### ConfigManager 方法

| 方法 | 说明 |
|------|------|
| `load(path?)` | 加载配置 |
| `save(path?)` | 保存配置 |
| `reset_to_default()` | 重置为默认 |
| `get_value(key, default?)` | 获取配置值 |
| `set_value(key, value, auto_save?)` | 设置配置值 |
| `on_change(name, callback)` | 注册变更监听 |
| `remove_on_change(name)` | 移除监听 |
| `export_schema()` | 导出配置 schema |
| `get_all_config_files()` | 获取所有配置文件 |

### 配置属性访问

```python
# 直接访问
mgr.config.converter.directories
mgr.config.ui.theme
mgr.config.logging.level

# 使用点号语法
mgr.get_value("ui.window_width")
mgr.set_value("cache.enabled", False)
```
