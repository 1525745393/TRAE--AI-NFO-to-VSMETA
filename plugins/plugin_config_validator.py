#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件配置验证模块
提供强类型的配置 schema 定义和验证功能
"""

import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('plugin_config_validator')


class ConfigValidationError(Exception):
    """配置验证错误异常"""
    pass


class ConfigType(Enum):
    """配置类型枚举"""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"


@dataclass
class ConfigSchemaItem:
    """配置项 schema 定义"""
    type: ConfigType
    default: Any = None
    description: str = ""
    required: bool = False
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None  # 正则表达式模式
    items_schema: Optional['ConfigSchemaItem'] = None  # 列表项 schema


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        self.valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def merge(self, other: 'ValidationResult'):
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
    
    def __str__(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"错误: {'; '.join(self.errors)}")
        if self.warnings:
            parts.append(f"警告: {'; '.join(self.warnings)}")
        if self.valid:
            return "验证通过"
        return "; ".join(parts)


class ConfigValidator:
    """
    配置验证器
    
    提供配置 schema 定义和验证功能，支持：
    - 类型检查
    - 范围验证
    - 长度验证
    - 正则表达式验证
    - 枚举值验证
    """
    
    def __init__(self, schema: Dict[str, ConfigSchemaItem] = None):
        """
        初始化验证器
        
        Args:
            schema: 配置 schema 字典，键为配置名，值为 ConfigSchemaItem
        """
        self.schema = schema or {}
        self._custom_validators = {}
    
    def add_schema_item(self, key: str, item: ConfigSchemaItem):
        """添加配置项 schema"""
        self.schema[key] = item
    
    def register_validator(self, key: str, validator_func: callable):
        """
        注册自定义验证函数
        
        Args:
            key: 配置项名称
            validator_func: 验证函数，接收 (key, value) 参数，返回 (bool, error_msg)
        """
        self._custom_validators[key] = validator_func
    
    def validate(self, config: Dict[str, Any], strict: bool = False) -> ValidationResult:
        """
        验证配置
        
        Args:
            config: 要验证的配置字典
            strict: 是否严格模式（不允许未知配置项）
            
        Returns:
            ValidationResult 验证结果
        """
        result = ValidationResult(valid=True)
        
        # 检查必需的配置项
        for key, schema_item in self.schema.items():
            if schema_item.required and key not in config:
                result.add_error(f"必需的配置项 '{key}' 缺失")
        
        # 验证每个配置项
        for key, value in config.items():
            if key not in self.schema:
                if strict:
                    result.add_error(f"未知配置项: '{key}'")
                else:
                    result.add_warning(f"未知配置项: '{key}' (已忽略)")
                continue
            
            schema_item = self.schema[key]
            item_result = self._validate_item(key, value, schema_item)
            result.merge(item_result)
        
        # 执行自定义验证
        for key, validator_func in self._custom_validators.items():
            if key in config:
                try:
                    is_valid, error_msg = validator_func(key, config[key])
                    if not is_valid:
                        result.add_error(f"{key}: {error_msg}")
                except Exception as e:
                    result.add_error(f"{key}: 自定义验证失败 - {e}")
        
        if not result.valid:
            logger.warning(f"配置验证失败: {result}")
        
        return result
    
    def _validate_item(self, key: str, value: Any, schema: ConfigSchemaItem) -> ValidationResult:
        """验证单个配置项"""
        result = ValidationResult(valid=True)
        
        # 类型检查
        if not self._check_type(value, schema.type):
            result.add_error(
                f"'{key}' 类型错误: 期望 {schema.type.value}, 实际 {type(value).__name__}"
            )
            return result
        
        # 值验证（如果是基本类型）
        if schema.type in (ConfigType.INT, ConfigType.FLOAT):
            if schema.min_value is not None and value < schema.min_value:
                result.add_error(f"'{key}' 小于最小值: {value} < {schema.min_value}")
            if schema.max_value is not None and value > schema.max_value:
                result.add_error(f"'{key}' 超过最大值: {value} > {schema.max_value}")
        
        # 长度验证（字符串和列表）
        if schema.type == ConfigType.STRING:
            if schema.min_length is not None and len(value) < schema.min_length:
                result.add_error(f"'{key}' 长度小于最小值: {len(value)} < {schema.min_length}")
            if schema.max_length is not None and len(value) > schema.max_length:
                result.add_error(f"'{key}' 长度超过最大值: {len(value)} > {schema.max_length}")
            
            # 正则表达式验证
            if schema.pattern is not None:
                import re
                if not re.match(schema.pattern, value):
                    result.add_error(f"'{key}' 不匹配模式: {schema.pattern}")
        
        if schema.type == ConfigType.LIST:
            if schema.min_length is not None and len(value) < schema.min_length:
                result.add_error(f"'{key}' 列表长度小于最小值: {len(value)} < {schema.min_length}")
            if schema.max_length is not None and len(value) > schema.max_length:
                result.add_error(f"'{key}' 列表长度超过最大值: {len(value)} > {schema.max_length}")
            
            # 验证列表项
            if schema.items_schema is not None:
                for i, item in enumerate(value):
                    item_result = self._validate_item(f"{key}[{i}]", item, schema.items_schema)
                    result.merge(item_result)
        
        # 枚举值验证
        if schema.allowed_values is not None:
            if value not in schema.allowed_values:
                result.add_error(
                    f"'{key}' 不在允许值范围内: {value} not in {schema.allowed_values}"
                )
        
        return result
    
    def _check_type(self, value: Any, expected_type: ConfigType) -> bool:
        """检查值类型"""
        if expected_type == ConfigType.STRING:
            return isinstance(value, str)
        elif expected_type == ConfigType.INT:
            return isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == ConfigType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif expected_type == ConfigType.BOOL:
            return isinstance(value, bool)
        elif expected_type == ConfigType.LIST:
            return isinstance(value, list)
        elif expected_type == ConfigType.DICT:
            return isinstance(value, dict)
        return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {key: item.default for key, item in self.schema.items()}
    
    def generate_schema_dict(self) -> Dict[str, Any]:
        """生成 schema 字典（用于 Web UI）"""
        result = {}
        for key, item in self.schema.items():
            result[key] = {
                "type": item.type.value,
                "default": item.default,
                "description": item.description,
                "required": item.required,
            }
            if item.min_value is not None:
                result[key]["min"] = item.min_value
            if item.max_value is not None:
                result[key]["max"] = item.max_value
            if item.min_length is not None:
                result[key]["minLength"] = item.min_length
            if item.max_length is not None:
                result[key]["maxLength"] = item.max_length
            if item.allowed_values is not None:
                result[key]["allowedValues"] = item.allowed_values
            if item.pattern is not None:
                result[key]["pattern"] = item.pattern
        return result


def create_validator_from_plugin(plugin) -> ConfigValidator:
    """
    从插件的 config_schema 属性创建验证器
    
    Args:
        plugin: 插件实例
        
    Returns:
        ConfigValidator 实例
    """
    schema_dict = getattr(plugin, 'config_schema', {})
    
    validator = ConfigValidator()
    
    for key, item_schema in schema_dict.items():
        if isinstance(item_schema, dict):
            # 从字典创建 schema
            type_str = item_schema.get('type', 'string')
            try:
                config_type = ConfigType(type_str)
            except ValueError:
                logger.warning(f"未知配置类型: {type_str}, 使用 string")
                config_type = ConfigType.STRING
            
            schema_item = ConfigSchemaItem(
                type=config_type,
                default=item_schema.get('default'),
                description=item_schema.get('description', ''),
                required=item_schema.get('required', False),
                min_value=item_schema.get('min'),
                max_value=item_schema.get('max'),
                min_length=item_schema.get('minLength'),
                max_length=item_schema.get('maxLength'),
                allowed_values=item_schema.get('allowedValues'),
                pattern=item_schema.get('pattern')
            )
            validator.add_schema_item(key, schema_item)
    
    return validator


# 使用示例和预设验证器

def create_priority_validator() -> ConfigValidator:
    """创建优先级验证器"""
    validator = ConfigValidator()
    validator.add_schema_item("priority", ConfigSchemaItem(
        type=ConfigType.INT,
        default=50,
        description="插件优先级（0-100）",
        min_value=0,
        max_value=100
    ))
    return validator


def create_timeout_validator() -> ConfigValidator:
    """创建超时时间验证器"""
    validator = ConfigValidator()
    validator.add_schema_item("timeout", ConfigSchemaItem(
        type=ConfigType.FLOAT,
        default=30.0,
        description="执行超时时间（秒）",
        min_value=0.1,
        max_value=3600.0
    ))
    return validator


def create_memory_limit_validator() -> ConfigValidator:
    """创建内存限制验证器"""
    validator = ConfigValidator()
    validator.add_schema_item("memory_limit_mb", ConfigSchemaItem(
        type=ConfigType.INT,
        default=512,
        description="内存限制（MB）",
        min_value=16,
        max_value=8192
    ))
    return validator
