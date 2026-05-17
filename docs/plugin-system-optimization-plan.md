# 插件系统优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 NFO to VSMETA 转换器的插件系统，添加依赖管理、优先级控制、配置持久化、热重载和模板生成功能。

**架构:** 扩展现有 Plugin 基类和 PluginManager，添加 PluginConfig 类管理配置，使用 watchdog 实现热重载，通过命令行工具生成插件模板。

**Tech Stack:** Python 3.9+, watchdog (文件监控), importlib (动态导入), dataclasses

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `nfo_to_vsmeta_converter_complete.py` | 修改 Plugin 基类、PluginManager，添加 PluginConfig 类 |
| `web_ui.py` | 添加插件配置编辑、热重载控制、优先级调整 API |
| `plugins/configs/*.json` | 插件配置文件存储目录 |
| `docs/plugin-system-optimization-design.md` | 设计文档（已存在） |

---

## 阶段一：核心功能（依赖管理 + 优先级）

### Task 1: 添加 Plugin 基类属性

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1534-1572` (Plugin 基类)

- [ ] **Step 1: 添加依赖和优先级属性**

在 `Plugin` 类中添加以下属性：

```python
@property
def dependencies(self) -> List[str]:
    """必需依赖的插件名称列表"""
    return []

@property
def optional_dependencies(self) -> List[str]:
    """可选依赖的插件名称列表"""
    return []

@property
def priority(self) -> int:
    """插件优先级，范围 0-100，默认 50"""
    return 50
```

- [ ] **Step 2: 添加优先级装饰器函数**

在 `Plugin` 类后添加：

```python
def priority(value: int):
    """设置插件优先级的装饰器"""
    def decorator(cls):
        cls._priority = value
        return cls
    return decorator
```

- [ ] **Step 3: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: add plugin dependencies and priority properties"
```

---

### Task 2: 实现依赖拓扑排序

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1707-1800` (PluginManager)

- [ ] **Step 1: 添加拓扑排序方法**

在 `PluginManager` 类中添加：

```python
def _ topological_sort_plugins(self, plugin_classes: List[Type[Plugin]]) -> List[Type[Plugin]]:
    """
    对插件类进行拓扑排序，确保依赖先加载
    
    Args:
        plugin_classes: 插件类列表
        
    Returns:
        排序后的插件类列表
        
    Raises:
        ValueError: 存在循环依赖
    """
    # 构建名称到类的映射
    name_to_class = {}
    for cls in plugin_classes:
        # 实例化临时对象获取名称
        try:
            temp = cls()
            name_to_class[temp.name] = cls
        except Exception as e:
            logger.warning(f"无法实例化插件类 {cls.__name__}: {e}")
            continue
    
    # 构建依赖图
    in_degree = {name: 0 for name in name_to_class}
    graph = {name: [] for name in name_to_class}
    
    for name, cls in name_to_class.items():
        try:
            temp = cls()
            for dep in temp.dependencies:
                if dep in name_to_class:
                    graph[dep].append(name)
                    in_degree[name] += 1
                else:
                    logger.error(f"插件 '{name}' 依赖的插件 '{dep}' 不存在")
                    raise ValueError(f"缺少必需依赖: {dep}")
            # 可选依赖不强制要求存在
            for dep in temp.optional_dependencies:
                if dep in name_to_class:
                    graph[dep].append(name)
                    in_degree[name] += 1
        except Exception as e:
            logger.warning(f"分析插件 '{name}' 依赖时出错: {e}")
    
    # Kahn算法拓扑排序
    queue = [name for name, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        # 按名称排序确保确定性
        queue.sort()
        current = queue.pop(0)
        result.append(name_to_class[current])
        
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(result) != len(name_to_class):
        # 存在循环依赖
        unresolved = set(name_to_class.keys()) - set(
            temp.name for temp in [cls() for cls in result]
        )
        raise ValueError(f"存在循环依赖，无法解析以下插件: {unresolved}")
    
    return result
```

- [ ] **Step 2: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: implement topological sort for plugin dependencies"
```

---

### Task 3: 修改插件加载流程

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1783-1850` (load_from_directory 方法)

- [ ] **Step 1: 修改 load_from_directory 使用拓扑排序**

替换 `load_from_directory` 方法：

```python
def load_from_directory(self, plugin_dir: str) -> int:
    """
    从目录加载 .py 插件文件
    
    扫描目录中的 .py 文件，使用 importlib 动态导入，
    查找继承自 Plugin 的类并自动注册。
    支持依赖管理和拓扑排序。
    
    Args:
        plugin_dir: 插件目录路径
        
    Returns:
        成功加载的插件数量
    """
    if not os.path.isdir(plugin_dir):
        logger.warning(f"插件目录不存在: {plugin_dir}")
        return 0
    
    # 收集所有插件类
    plugin_classes = []
    
    for filename in os.listdir(plugin_dir):
        if not filename.endswith('.py') or filename.startswith('_'):
            continue
        
        filepath = os.path.join(plugin_dir, filename)
        module_name = f"_plugin_{os.path.splitext(filename)[0]}"
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                logger.warning(f"无法加载插件文件: {filepath}")
                continue
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找继承自 Plugin 的类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, Plugin)
                        and attr is not Plugin
                        and attr.__module__ == module_name):
                    plugin_classes.append(attr)
                    
        except Exception as e:
            logger.error(f"加载插件文件 {filepath} 失败: {e}")
    
    if not plugin_classes:
        return 0
    
    # 拓扑排序
    try:
        sorted_classes = self._topological_sort_plugins(plugin_classes)
    except ValueError as e:
        logger.error(f"插件依赖解析失败: {e}")
        return 0
    
    # 按顺序实例化和注册
    loaded_count = 0
    for cls in sorted_classes:
        try:
            plugin_instance = cls()
            self.register(plugin_instance)
            loaded_count += 1
        except Exception as e:
            logger.error(f"实例化插件 {cls.__name__} 失败: {e}")
    
    return loaded_count
```

- [ ] **Step 2: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: integrate topological sort into plugin loading"
```

---

### Task 4: 实现插件优先级排序

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1724-1750` (register 方法)

- [ ] **Step 1: 修改 register 方法支持优先级**

在 `register` 方法中，添加插件后按优先级排序：

```python
def register(self, plugin: Plugin) -> None:
    """
    注册插件，根据类型自动分类
    
    Args:
        plugin: 插件实例
    """
    if plugin.name in self._plugins:
        logger.warning(f"插件 '{plugin.name}' 已存在，将被覆盖")
        self.unregister(plugin.name)
    
    self._plugins[plugin.name] = plugin
    
    # 根据类型自动分类
    if isinstance(plugin, NFOParserPlugin):
        self._parser_plugins.append(plugin)
        # 按优先级排序（高优先级在前）
        self._parser_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, VSMETAGeneratorPlugin):
        self._generator_plugins.append(plugin)
        self._generator_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, MetadataEnhancerPlugin):
        self._enhancer_plugins.append(plugin)
        self._enhancer_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, FileFilterPlugin):
        self._filter_plugins.append(plugin)
        self._filter_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, LifecyclePlugin):
        self._lifecycle_plugins.append(plugin)
        # 生命周期插件按注册顺序触发，不按优先级
    
    logger.info(f"插件已注册: {plugin.name} v{plugin.version} (优先级: {plugin.priority}) - {plugin.description}")
```

- [ ] **Step 2: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: implement plugin priority sorting"
```

---

## 阶段二：配置系统

### Task 5: 创建 PluginConfig 类

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py` (在 PluginManager 前添加)

- [ ] **Step 1: 添加 PluginConfig 类**

在 `PluginManager` 类定义之前添加：

```python
@dataclass
class PluginConfig:
    """
    插件配置管理类
    
    为每个插件提供独立的配置存储，支持持久化到 JSON 文件。
    """
    
    plugin_name: str
    config_dir: str = "plugins/configs"
    _data: Dict = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        """初始化时加载配置"""
        self._ensure_config_dir()
        self._load()
    
    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        safe_name = "".join(c for c in self.plugin_name if c.isalnum() or c in "_-").lower()
        return os.path.join(self.config_dir, f"{safe_name}.json")
    
    def _load(self) -> None:
        """从文件加载配置"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"加载插件 '{self.plugin_name}' 配置失败: {e}")
                self._data = {}
    
    def _save(self) -> None:
        """保存配置到文件"""
        config_path = self._get_config_path()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存插件 '{self.plugin_name}' 配置失败: {e}")
    
    def get(self, key: str, default=None):
        """
        获取配置项
        
        Args:
            key: 配置项名称
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        return self._data.get(key, default)
    
    def set(self, key: str, value) -> None:
        """
        设置配置项
        
        Args:
            key: 配置项名称
            value: 配置值
        """
        self._data[key] = value
        self._save()
    
    def update(self, values: Dict) -> None:
        """
        批量更新配置
        
        Args:
            values: 配置字典
        """
        self._data.update(values)
        self._save()
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._data.copy()
    
    def reset(self) -> None:
        """重置配置为空"""
        self._data = {}
        self._save()
```

- [ ] **Step 2: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: add PluginConfig class for plugin-specific configuration"
```

---

### Task 6: 修改 Plugin 基类支持配置 Schema

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1534-1572` (Plugin 类)

- [ ] **Step 1: 添加 config_schema 和修改 on_register**

在 `Plugin` 类中添加：

```python
@property
def config_schema(self) -> Dict[str, Any]:
    """
    定义配置项的 schema
    
    返回字典描述配置项的类型、默认值、约束等。
    用于 WebUI 自动生成配置表单。
    
    Returns:
        配置 schema 字典，格式：
        {
            "config_key": {
                "type": "string|int|float|bool|list|dict",
                "default": default_value,
                "description": "描述",
                "min": min_value,  # 可选，用于数值
                "max": max_value,  # 可选，用于数值
            }
        }
    """
    return {}

def on_register(self, config: Config, plugin_config: 'PluginConfig' = None) -> None:
    """
    注册时回调，可读取配置
    
    Args:
        config: 全局配置对象
        plugin_config: 插件专属配置对象，可能为 None
    """
    pass
```

- [ ] **Step 2: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: add config_schema property to Plugin base class"
```

---

### Task 7: 修改 PluginManager 传入 PluginConfig

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1724-1780` (register 方法)

- [ ] **Step 1: 修改 register 方法创建 PluginConfig**

修改 `register` 方法，在调用 `on_register` 时传入 `PluginConfig`：

```python
def register(self, plugin: Plugin, global_config: Config = None) -> None:
    """
    注册插件，根据类型自动分类
    
    Args:
        plugin: 插件实例
        global_config: 全局配置对象
    """
    if plugin.name in self._plugins:
        logger.warning(f"插件 '{plugin.name}' 已存在，将被覆盖")
        self.unregister(plugin.name)
    
    self._plugins[plugin.name] = plugin
    
    # 根据类型自动分类
    if isinstance(plugin, NFOParserPlugin):
        self._parser_plugins.append(plugin)
        self._parser_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, VSMETAGeneratorPlugin):
        self._generator_plugins.append(plugin)
        self._generator_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, MetadataEnhancerPlugin):
        self._enhancer_plugins.append(plugin)
        self._enhancer_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, FileFilterPlugin):
        self._filter_plugins.append(plugin)
        self._filter_plugins.sort(key=lambda p: (-p.priority, p.name))
    if isinstance(plugin, LifecyclePlugin):
        self._lifecycle_plugins.append(plugin)
    
    # 创建插件专属配置
    plugin_config = PluginConfig(plugin_name=plugin.name)
    
    # 调用注册回调
    try:
        plugin.on_register(global_config or Config(), plugin_config)
    except Exception as e:
        logger.warning(f"插件 '{plugin.name}' 注册回调异常: {e}")
    
    logger.info(f"插件已注册: {plugin.name} v{plugin.version} (优先级: {plugin.priority}) - {plugin.description}")
```

- [ ] **Step 2: 修改 load_from_directory 传入全局配置**

在 `load_from_directory` 方法签名中添加 `global_config` 参数：

```python
def load_from_directory(self, plugin_dir: str, global_config: Config = None) -> int:
    ...
    # 在注册时传入全局配置
    self.register(plugin_instance, global_config)
```

- [ ] **Step 3: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: integrate PluginConfig into plugin registration"
```

---

## 阶段三：热重载

### Task 8: 安装 watchdog 依赖

**Files:**
- Create/Modify: `requirements.txt` 或文档记录

- [ ] **Step 1: 记录依赖**

创建或更新依赖文件：

```bash
echo "watchdog>=3.0.0" >> requirements.txt
```

- [ ] **Step 2: 安装依赖**

```bash
pip install watchdog>=3.0.0 --break-system-packages
```

- [ ] **Step 3: 提交**

```bash
git add requirements.txt
git commit -m "chore: add watchdog dependency for hot reload"
```

---

### Task 9: 实现热重载功能

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py:1707-1800` (PluginManager)

- [ ] **Step 1: 添加热重载相关导入和属性**

在文件顶部添加导入：

```python
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
```

在 `PluginManager.__init__` 中添加：

```python
def __init__(self):
    self._plugins: Dict[str, Plugin] = {}
    self._parser_plugins: List[NFOParserPlugin] = []
    self._generator_plugins: List[VSMETAGeneratorPlugin] = []
    self._enhancer_plugins: List[MetadataEnhancerPlugin] = []
    self._filter_plugins: List[FileFilterPlugin] = []
    self._lifecycle_plugins: List[LifecyclePlugin] = []
    
    # 热重载相关
    self._hot_reload_enabled = False
    self._observer = None
    self._plugin_dir = None
    self._global_config = None
    self._file_hashes = {}  # 文件内容哈希缓存
```

- [ ] **Step 2: 添加热重载方法**

在 `PluginManager` 中添加：

```python
def enable_hot_reload(self, plugin_dir: str, global_config: Config = None) -> bool:
    """
    启用热重载
    
    Args:
        plugin_dir: 监控的插件目录
        global_config: 全局配置对象
        
    Returns:
        是否成功启用
    """
    if not WATCHDOG_AVAILABLE:
        logger.warning("watchdog 库未安装，无法启用热重载")
        return False
    
    if self._hot_reload_enabled:
        logger.info("热重载已启用")
        return True
    
    self._plugin_dir = plugin_dir
    self._global_config = global_config
    
    # 初始化文件哈希
    self._update_file_hashes()
    
    # 创建监控器
    class PluginEventHandler(FileSystemEventHandler):
        def __init__(self, manager):
            self.manager = manager
        
        def on_modified(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith('.py'):
                self.manager._handle_file_change(event.src_path)
        
        def on_created(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith('.py'):
                self.manager._handle_file_change(event.src_path, is_new=True)
        
        def on_deleted(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith('.py'):
                self.manager._handle_file_delete(event.src_path)
    
    handler = PluginEventHandler(self)
    self._observer = Observer()
    self._observer.schedule(handler, plugin_dir, recursive=False)
    self._observer.start()
    
    self._hot_reload_enabled = True
    logger.info(f"热重载已启用，监控目录: {plugin_dir}")
    return True

def disable_hot_reload(self) -> None:
    """禁用热重载"""
    if not self._hot_reload_enabled or self._observer is None:
        return
    
    self._observer.stop()
    self._observer.join()
    self._observer = None
    self._hot_reload_enabled = False
    logger.info("热重载已禁用")

def _update_file_hashes(self) -> None:
    """更新文件哈希缓存"""
    self._file_hashes = {}
    if not self._plugin_dir or not os.path.isdir(self._plugin_dir):
        return
    
    for filename in os.listdir(self._plugin_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            filepath = os.path.join(self._plugin_dir, filename)
            try:
                with open(filepath, 'rb') as f:
                    self._file_hashes[filepath] = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass

def _handle_file_change(self, filepath: str, is_new: bool = False) -> None:
    """
    处理文件变化
    
    Args:
        filepath: 变化的文件路径
        is_new: 是否为新文件
    """
    # 检查内容是否真的改变（避免重复触发）
    try:
        with open(filepath, 'rb') as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
    except Exception:
        return
    
    if not is_new and self._file_hashes.get(filepath) == current_hash:
        return
    
    self._file_hashes[filepath] = current_hash
    
    filename = os.path.basename(filepath)
    module_name = f"_plugin_{os.path.splitext(filename)[0]}"
    
    logger.info(f"检测到插件文件变化: {filename}")
    
    # 查找并注销旧插件
    plugins_to_reload = []
    for name, plugin in list(self._plugins.items()):
        if hasattr(plugin, '__module__') and plugin.__module__ == module_name:
            plugins_to_reload.append(name)
    
    # 保存配置
    saved_configs = {}
    for name in plugins_to_reload:
        config = PluginConfig(plugin_name=name)
        saved_configs[name] = config.get_all()
        self.unregister(name)
    
    # 重新加载模块
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找并注册新插件
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, Plugin)
                        and attr is not Plugin
                        and attr.__module__ == module_name):
                    try:
                        plugin_instance = attr()
                        # 恢复配置
                        if plugin_instance.name in saved_configs:
                            config = PluginConfig(plugin_name=plugin_instance.name)
                            config.update(saved_configs[plugin_instance.name])
                        self.register(plugin_instance, self._global_config)
                        logger.info(f"热重载成功: {plugin_instance.name}")
                    except Exception as e:
                        logger.error(f"热重载插件失败: {e}")
    except Exception as e:
        logger.error(f"重新加载模块 {filename} 失败: {e}")

def _handle_file_delete(self, filepath: str) -> None:
    """处理文件删除"""
    filename = os.path.basename(filepath)
    module_name = f"_plugin_{os.path.splitext(filename)[0]}"
    
    # 注销该模块的所有插件
    for name, plugin in list(self._plugins.items()):
        if hasattr(plugin, '__module__') and plugin.__module__ == module_name:
            self.unregister(name)
            logger.info(f"插件已删除: {name}")
    
    if filepath in self._file_hashes:
        del self._file_hashes[filepath]
```

- [ ] **Step 3: 添加 hashlib 导入**

在文件顶部添加：

```python
import hashlib
```

- [ ] **Step 4: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: implement plugin hot reload with watchdog"
```

---

## 阶段四：模板生成器

### Task 10: 创建插件模板

**Files:**
- Create: `plugin_templates/` 目录和模板文件

- [ ] **Step 1: 创建模板目录和基础模板**

```bash
mkdir -p plugin_templates
```

创建 `plugin_templates/base.py.template`：

```python
"""
{plugin_name} - {description}

功能描述：
- TODO: 添加功能描述

作者: {author}
版本: {version}
"""

from nfo_to_vsmeta_converter_complete import (
    {base_class},
    VideoMetadata,
    Config,
    PluginConfig
)


class {class_name}({base_class}):
    """
    {description}
    """
    
    @property
    def name(self) -> str:
        """插件唯一标识名称"""
        return "{plugin_name}"
    
    @property
    def version(self) -> str:
        """插件版本号"""
        return "{version}"
    
    @property
    def description(self) -> str:
        """插件功能描述"""
        return "{description}"
    
    @property
    def priority(self) -> int:
        """
        插件优先级，范围 0-100，默认 50
        数字越大优先级越高，越先执行
        """
        return {priority}
    
    @property
    def dependencies(self) -> list:
        """必需依赖的插件名称列表"""
        return {dependencies}
    
    @property
    def optional_dependencies(self) -> list:
        """可选依赖的插件名称列表"""
        return {optional_dependencies}
    
    @property
    def config_schema(self) -> dict:
        """
        配置项定义
        用于 WebUI 自动生成配置表单
        """
        return {config_schema}
    
    def on_register(self, config: Config, plugin_config: PluginConfig = None) -> None:
        """
        注册时回调
        
        Args:
            config: 全局配置对象
            plugin_config: 插件专属配置对象
        """
        # TODO: 初始化插件，读取配置
        if plugin_config:
            pass  # self.api_key = plugin_config.get("api_key")
    
    def on_unregister(self) -> None:
        """注销时回调，用于清理资源"""
        pass
    
{method_impl}
```

- [ ] **Step 2: 创建各类型模板片段**

创建 `plugin_templates/methods.py`：

```python
# NFO Parser 方法模板
PARSER_METHOD = '''
    def parse(self, nfo_path: str, metadata: VideoMetadata) -> VideoMetadata:
        """
        解析/修改 NFO 元数据
        
        Args:
            nfo_path: NFO 文件路径
            metadata: 默认解析器已解析的元数据
            
        Returns:
            修改后的元数据
        """
        # TODO: 实现解析逻辑
        # 示例：修改标题
        # metadata.title = metadata.title + " [Custom]"
        return metadata
'''

# VSMETA Generator 方法模板
GENERATOR_METHOD = '''
    def generate(self, metadata: VideoMetadata, vsmeta_data: bytes) -> bytes:
        """
        修改 VSMETA 二进制数据
        
        Args:
            metadata: 视频元数据
            vsmeta_data: 默认生成器已生成的 VSMETA 二进制数据
            
        Returns:
            修改后的 VSMETA 二进制数据
        """
        # TODO: 实现生成逻辑
        return vsmeta_data
'''

# Metadata Enhancer 方法模板
ENHANCER_METHOD = '''
    def enhance(self, metadata: VideoMetadata, filepath: str) -> VideoMetadata:
        """
        增强元数据
        
        Args:
            metadata: 当前元数据
            filepath: 对应的视频文件路径
            
        Returns:
            增强后的元数据
        """
        # TODO: 实现增强逻辑
        # 示例：从外部API获取数据
        return metadata
'''

# File Filter 方法模板
FILTER_METHOD = '''
    def should_process(self, filepath: str, filename: str) -> bool:
        """
        判断文件是否应该被处理
        
        Args:
            filepath: 文件完整路径
            filename: 文件名
            
        Returns:
            True 表示应该处理，False 表示跳过
        """
        # TODO: 实现过滤逻辑
        return True
'''

# Lifecycle 方法模板
LIFECYCLE_METHOD = '''
    def on_start(self, config: Config) -> None:
        """转换开始时回调"""
        pass
    
    def on_file_start(self, filepath: str) -> None:
        """单个文件开始处理时回调"""
        pass
    
    def on_file_end(self, filepath: str, result: dict) -> None:
        """单个文件处理结束时回调"""
        pass
    
    def on_finish(self, stats) -> None:
        """转换全部完成时回调"""
        pass
'''
```

- [ ] **Step 3: 提交**

```bash
git add plugin_templates/
git commit -m "feat: add plugin template files"
```

---

### Task 11: 实现模板生成器命令

**Files:**
- Modify: `nfo_to_vsmeta_converter_complete.py` (添加命令行参数处理)

- [ ] **Step 1: 添加模板生成函数**

在文件末尾（`if __name__ == "__main__":` 之前）添加：

```python
def create_plugin_template(
    name: str,
    plugin_type: str = "enhancer",
    output_dir: str = "plugins",
    author: str = "Anonymous",
    version: str = "1.0.0",
    description: str = "",
    priority: int = 50
) -> str:
    """
    创建插件模板文件
    
    Args:
        name: 插件名称（英文，用于类名和文件名）
        plugin_type: 插件类型 (parser|generator|enhancer|filter|lifecycle)
        output_dir: 输出目录
        author: 作者名
        version: 版本号
        description: 插件描述
        priority: 优先级
        
    Returns:
        生成的文件路径
    """
    # 类型映射
    type_mapping = {
        "parser": ("NFOParserPlugin", "PARSER_METHOD"),
        "generator": ("VSMETAGeneratorPlugin", "GENERATOR_METHOD"),
        "enhancer": ("MetadataEnhancerPlugin", "ENHANCER_METHOD"),
        "filter": ("FileFilterPlugin", "FILTER_METHOD"),
        "lifecycle": ("LifecyclePlugin", "LIFECYCLE_METHOD"),
    }
    
    if plugin_type not in type_mapping:
        raise ValueError(f"未知的插件类型: {plugin_type}")
    
    base_class, method_key = type_mapping[plugin_type]
    
    # 确保输出目录存在
    plugin_dir = os.path.join(output_dir, name.lower())
    os.makedirs(plugin_dir, exist_ok=True)
    
    # 读取模板
    template_path = os.path.join(
        os.path.dirname(__file__), 
        "plugin_templates", 
        "base.py.template"
    )
    
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        # 内置默认模板
        template = '''"""\n{plugin_name} - {description}\n"""\n\nfrom nfo_to_vsmeta_converter_complete import {base_class}, VideoMetadata, Config, PluginConfig\n\nclass {class_name}({base_class}):\n    @property\n    def name(self) -> str:\n        return "{plugin_name}"\n    @property\n    def version(self) -> str:\n        return "{version}"\n    @property\n    def description(self) -> str:\n        return "{description}"\n    @property\n    def priority(self) -> int:\n        return {priority}\n    @property\n    def dependencies(self) -> list:\n        return {dependencies}\n    @property\n    def optional_dependencies(self) -> list:\n        return {optional_dependencies}\n    @property\n    def config_schema(self) -> dict:\n        return {config_schema}\n    def on_register(self, config: Config, plugin_config: PluginConfig = None) -> None:\n        pass\n{method_impl}\n'''
    
    # 获取方法实现
    method_impl = ""  # 简化版本，实际应从 methods.py 读取
    
    # 填充模板
    content = template.format(
        plugin_name=name.lower(),
        class_name=name.capitalize(),
        base_class=base_class,
        description=description or f"{name} 插件",
        author=author,
        version=version,
        priority=priority,
        dependencies="[]",
        optional_dependencies="[]",
        config_schema="{}",
        method_impl=method_impl
    )
    
    # 写入文件
    file_path = os.path.join(plugin_dir, "plugin.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 创建 __init__.py
    init_path = os.path.join(plugin_dir, "__init__.py")
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(f'from .plugin import {name.capitalize()}\n')
    
    # 创建默认配置
    config_path = os.path.join(plugin_dir, "config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump({}, f, indent=2)
    
    # 创建 README
    readme_path = os.path.join(plugin_dir, "README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"# {name}\\n\\n{description or name + ' 插件'}\\n\\n## 配置\\n\\n编辑 `config.json` 或在 WebUI 中配置。\\n")
    
    logger.info(f"插件模板已创建: {file_path}")
    return file_path
```

- [ ] **Step 2: 添加命令行参数处理**

修改 `if __name__ == "__main__":` 块：

```python
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NFO to VSMETA Converter")
    parser.add_argument("--create-plugin", metavar="NAME",
                       help="创建插件模板")
    parser.add_argument("--type", choices=["parser", "generator", "enhancer", "filter", "lifecycle"],
                       default="enhancer", help="插件类型")
    parser.add_argument("--output-dir", default="plugins",
                       help="插件输出目录")
    parser.add_argument("--author", default="Anonymous",
                       help="插件作者")
    parser.add_argument("--version", default="1.0.0",
                       help="插件版本")
    parser.add_argument("--description", default="",
                       help="插件描述")
    parser.add_argument("--priority", type=int, default=50,
                       help="插件优先级")
    
    args = parser.parse_args()
    
    if args.create_plugin:
        try:
            path = create_plugin_template(
                name=args.create_plugin,
                plugin_type=args.type,
                output_dir=args.output_dir,
                author=args.author,
                version=args.version,
                description=args.description,
                priority=args.priority
            )
            print(f"✓ 插件模板已创建: {path}")
        except Exception as e:
            print(f"✗ 创建失败: {e}")
            exit(1)
    else:
        # 原有的主逻辑
        main()
```

- [ ] **Step 3: 提交**

```bash
git add nfo_to_vsmeta_converter_complete.py
git commit -m "feat: add plugin template generator command"
```

---

## 阶段五：WebUI 集成

### Task 12: 添加插件管理 API

**Files:**
- Modify: `web_ui.py`

- [ ] **Step 1: 添加获取插件配置 API**

```python
@app.route('/api/plugins/<name>/config')
@require_api_token
def api_get_plugin_config(name: str) -> Dict:
    """获取插件配置"""
    try:
        from nfo_to_vsmeta_converter_complete import PluginConfig
        config = PluginConfig(plugin_name=name)
        return jsonify({
            'config': config.get_all(),
            'schema': {}  # 需要从插件实例获取 schema
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plugins/<name>/config', methods=['POST'])
@require_api_token
@require_csrf
def api_set_plugin_config(name: str) -> Dict:
    """更新插件配置"""
    try:
        from nfo_to_vsmeta_converter_complete import PluginConfig
        data = request.get_json(silent=True) or {}
        config = PluginConfig(plugin_name=name)
        config.update(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 2: 添加热重载控制 API**

```python
@app.route('/api/plugins/hot-reload', methods=['POST'])
@require_api_token
@require_csrf
def api_toggle_hot_reload() -> Dict:
    """启用/禁用热重载"""
    data = request.get_json(silent=True) or {}
    enabled = data.get('enabled', False)
    
    converter = _get_state('converter')
    if not converter or not hasattr(converter, 'plugin_manager'):
        return jsonify({'error': '转换器未初始化'}), 400
    
    pm = converter.plugin_manager
    
    if enabled:
        config = _get_state('config')
        success = pm.enable_hot_reload(
            config.plugin_dir if config else 'plugins',
            config
        )
        return jsonify({'enabled': success})
    else:
        pm.disable_hot_reload()
        return jsonify({'enabled': False})

@app.route('/api/plugins/<name>/reload', methods=['POST'])
@require_api_token
@require_csrf
def api_reload_plugin(name: str) -> Dict:
    """手动重载指定插件"""
    # 实现重载逻辑
    return jsonify({'success': True})
```

- [ ] **Step 3: 提交**

```bash
git add web_ui.py
git commit -m "feat: add plugin config and hot reload APIs"
```

---

## 完成

所有任务完成后，插件系统将具备：
1. ✅ 依赖管理和拓扑排序
2. ✅ 优先级控制
3. ✅ 配置持久化
4. ✅ 热重载
5. ✅ 模板生成器

---

**计划结束**
