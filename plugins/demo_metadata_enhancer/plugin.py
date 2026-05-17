"""
示例元数据增强插件

作者: Demo Author
版本: 1.0.0
类型: enhancer
"""

from nfo_to_vsmeta_converter_complete import (
    MetadataEnhancerPlugin,
    VideoMetadata,
    Config,
    PluginConfig,
)


class DemoMetadataEnhancer(MetadataEnhancerPlugin):
    """
    示例元数据增强插件
    """
    
    @property
    def name(self) -> str:
        """插件唯一标识名称"""
        return "demo_metadata_enhancer"
    
    @property
    def version(self) -> str:
        """插件版本号"""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """插件功能描述"""
        return "示例元数据增强插件"
    
    @property
    def priority(self) -> int:
        """插件优先级 (0-100)，数字越大越先执行"""
        return 50
    
    @property
    def dependencies(self) -> list:
        """必需依赖的插件名称列表"""
        return []
    
    @property
    def optional_dependencies(self) -> list:
        """可选依赖的插件名称列表"""
        return []
    
    @property
    def config_schema(self) -> dict:
        """
        配置项定义，用于 WebUI 自动生成配置表单
        格式: {"key": {"type": "string", "default": "", "description": "..."}}
        """
        return {}
    
    def on_register(self, config: Config, plugin_config: PluginConfig = None) -> None:
        """
        注册时回调
        
        Args:
            config: 全局配置对象
            plugin_config: 插件专属配置对象
        """
        # TODO: 初始化插件，读取配置
        # 示例: self.api_key = plugin_config.get("api_key") if plugin_config else ""
        pass
    
    def on_unregister(self) -> None:
        """注销时回调，用于清理资源"""
        pass

    def enhance(self, metadata: 'VideoMetadata', filepath: str) -> 'VideoMetadata':
        """
        增强元数据
        
        Args:
            metadata: 当前元数据
            filepath: 对应的视频文件路径
            
        Returns:
            增强后的元数据
        """
        # TODO: 实现增强逻辑
        return metadata

