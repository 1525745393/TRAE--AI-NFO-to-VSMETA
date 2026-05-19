#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置异常定义
"""


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件未找到"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass


class ConfigSaveError(ConfigError):
    """配置保存错误"""
    pass


class ConfigLoadError(ConfigError):
    """配置加载错误"""
    pass
