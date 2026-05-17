# 插件系统优化设计文档

**日期**: 2026-05-17  
**版本**: v1.0  
**方案**: B (P1+P2 - 核心功能增强 + 开发者体验)

---

## 1. 概述

### 1.1 目标
优化 NFO to VSMETA 转换器的插件系统，提供更强大的插件管理能力、更好的开发者体验和更灵活的配置机制。

### 1.2 范围
- 插件依赖管理
- 插件优先级/排序控制
- 插件配置持久化
- 插件热重载
- 插件模板生成器

### 1.3 非目标
- 插件市场/在线仓库
- 插件沙箱安全隔离
- 性能监控统计

---

## 2. 当前系统分析

### 2.1 现有功能
- 5种插件类型：NFO解析、VSMETA生成、元数据增强、文件过滤、生命周期钩子
- 动态加载机制（从目录加载.py文件）
- 插件注册/注销管理
- 生命周期回调

### 2.2 存在问题
1. 插件加载顺序不可控，无法处理依赖关系
2. 同类插件执行顺序固定，无法调整优先级
3. 插件配置与主配置混合，缺乏独立性
4. 开发插件时需要手动重启才能看到效果
5. 创建新插件需要复制粘贴样板代码

---

## 3. 详细设计

### 3.1 插件依赖管理

#### 3.1.1 接口设计

```python
class Plugin(ABC):
    @property
    def dependencies(self) -> List[str]:
        """
        必需依赖的插件名称列表
        这些插件必须在当前插件之前加载
        """
        return []
    
    @property
    def optional_dependencies(self) -> List[str]:
        """
        可选依赖的插件名称列表
        如果存在则先加载，不存在也不报错
        """
        return []
```

#### 3.1.2 加载流程

```
1. 扫描插件目录，收集所有插件类
2. 构建依赖图（有向图）
3. 拓扑排序确定加载顺序
4. 检测循环依赖
5. 按顺序实例化并注册插件
```

#### 3.1.3 错误处理

- **缺失必需依赖**: 报错并跳过该插件
- **循环依赖**: 检测并抛出 CycleDependencyError
- **版本不兼容**: （预留，未来扩展）

---

### 3.2 插件优先级/排序控制

#### 3.2.1 接口设计

```python
class Plugin(ABC):
    @property
    def priority(self) -> int:
        """
        插件优先级，范围 0-100，默认 50
        数字越大优先级越高，越先执行
        """
        return 50
```

#### 3.2.2 快捷装饰器

```python
def priority(value: int):
    """设置插件优先级的装饰器"""
    def decorator(cls):
        cls._priority = value
        return cls
    return decorator

# 使用示例
@priority(100)
class MyPlugin(NFOParserPlugin):
    pass
```

#### 3.2.3 排序规则

1. 按优先级降序排列
2. 同优先级按插件名称字母顺序
3. 生命周期插件按注册顺序触发

---

### 3.3 插件配置持久化

#### 3.3.1 配置架构

```python
@dataclass
class PluginConfig:
    """插件配置管理类"""
    plugin_name: str
    config_dir: str = "plugins/configs"
    _data: Dict = field(default_factory=dict)
    
    def get(self, key: str, default=None):
        return self._data.get(key, default)
    
    def set(self, key: str, value) -> None:
        self._data[key] = value
        self._save()
    
    def _save(self) -> None:
        """保存到 JSON 文件"""
        pass
```

#### 3.3.2 插件接口

```python
class Plugin(ABC):
    @property
    def config_schema(self) -> Dict[str, Any]:
        """
        定义配置项的 schema
        支持类型: string, int, float, bool, list, dict
        """
        return {
            "api_key": {
                "type": "string",
                "default": "",
                "description": "API密钥"
            },
            "timeout": {
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 300,
                "description": "超时时间(秒)"
            }
        }
    
    def on_register(self, config: Config, plugin_config: PluginConfig = None):
        """
        注册时回调
        
        Args:
            config: 全局配置对象
            plugin_config: 插件专属配置对象
        """
        pass
```

#### 3.3.3 存储结构

```
plugins/
  configs/
    my_plugin.json
    another_plugin.json
```

#### 3.3.4 WebUI 集成

- 插件管理页面显示每个插件的配置表单
- 根据 schema 自动生成输入控件
- 支持配置验证和错误提示

---

### 3.4 插件热重载

#### 3.4.1 监控机制

```python
class PluginManager:
    def __init__(self):
        self._hot_reload_enabled = False
        self._observer = None
        self._file_hashes = {}  # 文件内容哈希缓存
    
    def enable_hot_reload(self, plugin_dir: str, interval: float = 1.0):
        """
        启用热重载
        
        Args:
            plugin_dir: 监控的插件目录
            interval: 检查间隔（秒）
        """
        pass
    
    def disable_hot_reload(self):
        """禁用热重载"""
        pass
```

#### 3.4.2 实现方式

使用 `watchdog` 库监控文件系统事件：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PluginReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            self.reload_plugin(event.src_path)
    
    def on_created(self, event):
        if event.src_path.endswith('.py'):
            self.load_new_plugin(event.src_path)
```

#### 3.4.3 重载流程

```
1. 检测文件变化
2. 计算文件哈希，确认内容确实改变
3. 找到对应的插件实例
4. 保存插件当前配置
5. 注销旧插件
6. 重新导入模块（使用 importlib.reload）
7. 实例化新插件
8. 恢复配置
9. 重新注册
```

#### 3.4.4 WebUI 控制

- 插件页面添加"启用热重载"开关
- 显示热重载状态和最后重载时间
- 手动触发重载按钮

---

### 3.5 插件模板生成器

#### 3.5.1 命令行接口

```bash
# 生成插件脚手架
python nfo_to_vsmeta_converter_complete.py --create-plugin <name> --type <type>

# 参数
--type: parser | generator | enhancer | filter | lifecycle
--output-dir: 输出目录（默认 plugins/）
```

#### 3.5.2 生成的文件结构

```
plugins/
  my_plugin/
    __init__.py          # 导出插件类
    plugin.py            # 主插件类
    config.json          # 默认配置
    README.md            # 使用说明
    example.py           # 使用示例
```

#### 3.5.3 模板内容示例

**plugin.py** (enhancer 类型):

```python
"""
MyPlugin - 元数据增强插件

功能描述：
- 从外部API获取额外的元数据
- 补充缺失的影片信息
"""

from nfo_to_vsmeta_converter_complete import MetadataEnhancerPlugin, VideoMetadata

class MyPlugin(MetadataEnhancerPlugin):
    @property
    def name(self) -> str:
        return "my_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "从外部API获取额外的元数据"
    
    @property
    def priority(self) -> int:
        return 50
    
    @property
    def config_schema(self) -> dict:
        return {
            "api_key": {
                "type": "string",
                "default": "",
                "description": "API密钥"
            }
        }
    
    def on_register(self, config, plugin_config=None):
        self.api_key = plugin_config.get("api_key") if plugin_config else ""
    
    def enhance(self, metadata: VideoMetadata, filepath: str) -> VideoMetadata:
        """
        增强元数据
        
        Args:
            metadata: 当前元数据
            filepath: 视频文件路径
            
        Returns:
            增强后的元数据
        """
        # TODO: 实现增强逻辑
        return metadata
```

---

## 4. WebUI 集成

### 4.1 插件管理页面增强

新增功能：
- 显示插件依赖关系图
- 调整插件优先级（拖拽或输入数字）
- 编辑插件配置（根据 schema 生成表单）
- 热重载开关
- 手动重载按钮

### 4.2 API 扩展

```python
# 获取插件依赖图
GET /api/plugins/dependencies

# 更新插件优先级
POST /api/plugins/{name}/priority
{"priority": 75}

# 获取插件配置
GET /api/plugins/{name}/config

# 更新插件配置
POST /api/plugins/{name}/config
{"api_key": "xxx", "timeout": 60}

# 启用/禁用热重载
POST /api/plugins/hot-reload
{"enabled": true}

# 手动重载插件
POST /api/plugins/{name}/reload
```

---

## 5. 兼容性

### 5.1 向后兼容

- 现有插件无需修改即可继续工作
- `on_register` 方法的 `plugin_config` 参数为可选
- 默认优先级为 50，保持现有执行顺序

### 5.2 迁移指南

旧插件升级步骤：
1. 添加 `priority` 属性（可选）
2. 添加 `dependencies` 属性（可选）
3. 添加 `config_schema` 并使用 `plugin_config`（可选）

---

## 6. 实现计划

### 6.1 阶段一：核心功能
1. 实现插件依赖管理和拓扑排序
2. 实现插件优先级系统
3. 更新 PluginManager 支持新功能

### 6.2 阶段二：配置系统
1. 实现 PluginConfig 类
2. 修改插件加载流程，传入 plugin_config
3. WebUI 添加配置编辑功能

### 6.3 阶段三：热重载
1. 集成 watchdog 库
2. 实现文件监控和重载逻辑
3. WebUI 添加热重载控制

### 6.4 阶段四：模板生成器
1. 创建模板文件
2. 实现命令行接口
3. 添加使用文档

---

## 7. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 循环依赖导致加载失败 | 中 | 高 | 提供清晰的错误信息和检测工具 |
| 热重载时状态丢失 | 中 | 中 | 保存并恢复插件配置 |
| 优先级冲突 | 低 | 低 | 同优先级按名称排序，确保确定性 |
| 配置格式不兼容 | 低 | 中 | 版本控制和迁移脚本 |

---

## 8. 附录

### 8.1 依赖库

```
watchdog>=3.0.0  # 文件系统监控
```

### 8.2 相关文件

- `nfo_to_vsmeta_converter_complete.py` - 主转换器模块
- `web_ui.py` - Web 界面
- `plugins/` - 插件目录

---

**文档结束**
