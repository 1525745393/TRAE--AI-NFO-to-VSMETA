#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
实现集中式配置管理和持久化
"""

import os
import json
import logging
from typing import Any, Dict, Optional, Callable
from pathlib import Path

from .schemas import ConfigSchema
from .exceptions import (
    ConfigNotFoundError,
    ConfigValidationError,
    ConfigSaveError,
    ConfigLoadError,
)

logger = logging.getLogger("ConfigManager")


class ConfigManager:
    """
    配置管理器
    
    提供集中式配置管理功能：
    - 配置加载和保存
    - 配置验证
    - 配置变更监听
    - 配置备份
    """

    # 单例实例
    _instance: Optional["ConfigManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_dir: Optional[str] = None, auto_load: bool = True):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录，默认使用应用数据目录
            auto_load: 是否自动加载配置
        """
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._config_dir = self._get_config_dir(config_dir)
        self._config_file = self._config_dir / "config.json"
        self._backup_dir = self._config_dir / "backups"

        self._config = ConfigSchema()
        self._change_listeners: Dict[str, Callable[[ConfigSchema], None]] = {}

        # 确保目录存在
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        if auto_load:
            try:
                self.load()
            except ConfigNotFoundError:
                logger.info("配置文件不存在，使用默认配置")
                self._save_default_config()

    def _get_config_dir(self, config_dir: Optional[str]) -> Path:
        """获取配置目录"""
        if config_dir:
            return Path(config_dir).absolute()

        # 按优先级查找配置目录
        env_config_dir = os.environ.get("NFO_VSMETA_CONFIG_DIR")
        if env_config_dir:
            return Path(env_config_dir).absolute()

        # 使用用户数据目录
        home_dir = Path.home()

        if os.name == "nt":  # Windows
            config_dir = home_dir / "AppData" / "Local" / "NfoToVsmeta"
        elif os.name == "posix":
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "nfo_to_vsmeta"
            else:
                config_dir = home_dir / ".config" / "nfo_to_vsmeta"
        else:
            config_dir = home_dir / ".nfo_to_vsmeta"

        return config_dir.absolute()

    def _save_default_config(self):
        """保存默认配置"""
        try:
            self.save()
            logger.info("默认配置已保存")
        except Exception as e:
            logger.warning(f"保存默认配置失败: {e}")

    @property
    def config(self) -> ConfigSchema:
        """获取配置对象"""
        return self._config

    @property
    def config_dir(self) -> Path:
        """获取配置目录"""
        return self._config_dir

    @property
    def config_file(self) -> Path:
        """获取配置文件路径"""
        return self._config_file

    def load(self, config_path: Optional[str] = None) -> "ConfigManager":
        """
        加载配置
        
        Args:
            config_path: 配置文件路径，默认使用标准位置
            
        Returns:
            ConfigManager 自身（链式调用）
            
        Raises:
            ConfigNotFoundError: 配置文件不存在
            ConfigLoadError: 加载失败
        """
        target_path = Path(config_path) if config_path else self._config_file

        if not target_path.exists():
            raise ConfigNotFoundError(f"配置文件不存在: {target_path}")

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._config = ConfigSchema.from_dict(data)
            self._config.validate_all()

            logger.info(f"配置已从 {target_path} 加载")
            self._notify_change_listeners()

            return self
        except json.JSONDecodeError as e:
            raise ConfigLoadError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigLoadError(f"加载配置失败: {e}")

    def save(self, config_path: Optional[str] = None, create_backup: bool = True) -> "ConfigManager":
        """
        保存配置
        
        Args:
            config_path: 保存路径，默认使用标准位置
            create_backup: 是否创建备份
            
        Returns:
            ConfigManager 自身（链式调用）
            
        Raises:
            ConfigSaveError: 保存失败
        """
        target_path = Path(config_path) if config_path else self._config_file

        try:
            self._config.validate_all()

            # 创建备份
            if create_backup and target_path.exists():
                self._create_backup(target_path)

            # 保存新配置
            data = self._config.to_dict()

            # 先保存到临时文件，然后原子替换
            temp_path = target_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            if target_path.exists():
                target_path.replace(temp_path)
            else:
                temp_path.rename(target_path)

            logger.info(f"配置已保存到 {target_path}")
            self._notify_change_listeners()

            return self
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise ConfigSaveError(f"保存配置失败: {e}")

    def _create_backup(self, config_path: Path):
        """创建配置备份"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._backup_dir / f"config_{timestamp}.json"

            import shutil
            shutil.copy2(config_path, backup_path)

            # 清理旧备份（保留最近10个）
            backups = sorted(self._backup_dir.glob("config_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            for old_backup in backups[10:]:
                old_backup.unlink(missing_ok=True)

            logger.debug(f"配置已备份到 {backup_path}")
        except Exception as e:
            logger.warning(f"创建配置备份失败: {e}")

    def reset_to_default(self) -> "ConfigManager":
        """重置为默认配置"""
        self._config = ConfigSchema()
        logger.info("配置已重置为默认值")
        self._notify_change_listeners()
        return self

    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（便捷方法）
        
        Args:
            key: 配置键，支持点号分隔，如 "ui.theme"
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config

        try:
            for k in keys:
                value = getattr(value, k)
            return value
        except (AttributeError, KeyError):
            return default

    def set_value(self, key: str, value: Any, auto_save: bool = True):
        """
        设置配置值（便捷方法）
        
        Args:
            key: 配置键，支持点号分隔
            value: 新值
            auto_save: 是否自动保存
        """
        keys = key.split(".")
        obj = self._config

        try:
            for k in keys[:-1]:
                obj = getattr(obj, k)
            setattr(obj, keys[-1], value)

            if auto_save:
                self.save()

            logger.debug(f"配置已更新: {key} = {value}")
        except (AttributeError, KeyError) as e:
            raise ConfigValidationError(f"无法设置配置值 {key}: {e}")

    def on_change(self, name: str, callback: Callable[[ConfigSchema], None]):
        """
        注册配置变更监听器
        
        Args:
            name: 监听器名称
            callback: 回调函数，接收 ConfigSchema 参数
        """
        self._change_listeners[name] = callback

    def remove_on_change(self, name: str):
        """移除配置变更监听器"""
        if name in self._change_listeners:
            del self._change_listeners[name]

    def _notify_change_listeners(self):
        """通知所有配置变更监听器"""
        for name, callback in self._change_listeners.items():
            try:
                callback(self._config)
            except Exception as e:
                logger.error(f"配置变更监听器 {name} 执行失败: {e}")

    def export_schema(self) -> Dict[str, Any]:
        """导出配置 schema（用于 UI 渲染）"""
        return {
            "version": self._config.version,
            "converter": {
                "directories": {"type": "list", "default": ["."], "label": "目录"},
                "max_workers": {"type": "int", "default": 4, "min": 1, "max": 32, "label": "最大工作线程"},
                "max_image_size_kb": {"type": "int", "default": 200, "min": 50, "max": 10000, "label": "最大图片大小(KB)"},
                "image_compression_ratio": {"type": "float", "default": 0.8, "min": 0.1, "max": 1.0, "label": "压缩比例"},
                "auto_backup": {"type": "bool", "default": True, "label": "自动备份"},
                "skip_existing": {"type": "bool", "default": True, "label": "跳过已存在"},
            },
            "ui": {
                "theme": {"type": "select", "default": "dark", "options": ["dark", "light", "ocean", "forest"], "label": "主题"},
                "window_width": {"type": "int", "default": 1280, "min": 800, "max": 3840, "label": "窗口宽度"},
                "window_height": {"type": "int", "default": 800, "min": 600, "max": 2160, "label": "窗口高度"},
            },
        }

    def get_all_config_files(self) -> list:
        """获取所有配置文件（包括备份）"""
        files = []
        if self._config_file.exists():
            files.append(str(self._config_file))
        files.extend([str(f) for f in sorted(self._backup_dir.glob("config_*.json"))])
        return files


# 全局单例访问函数
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """
    获取配置管理器实例（单例）
    
    Args:
        config_dir: 配置目录
        
    Returns:
        ConfigManager 实例
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager(config_dir)
    return _config_manager_instance
