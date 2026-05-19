#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件沙箱模块
提供插件执行的安全隔离、超时控制和资源限制
"""

import time
import logging
import resource
import concurrent.futures
from typing import Any, Callable, Optional
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger('plugin_sandbox')


class PluginTimeoutError(Exception):
    """插件执行超时异常"""
    pass


class PluginExecutionError(Exception):
    """插件执行错误异常"""
    pass


class PluginResourceLimitError(Exception):
    """插件资源限制异常"""
    pass


@dataclass
class SandboxConfig:
    """沙箱配置"""
    timeout: float = 30.0  # 执行超时时间（秒）
    memory_limit_mb: int = 512  # 内存限制（MB）
    enable_timeout: bool = True  # 是否启用超时控制
    enable_memory_limit: bool = True  # 是否启用内存限制
    enable_cpu_limit: bool = False  # 是否启用 CPU 限制
    max_cpu_percent: int = 80  # 最大 CPU 使用率


class PluginSandbox:
    """
    插件沙箱
    
    提供安全的插件执行环境，包括：
    - 超时控制：防止插件无限执行
    - 内存限制：防止内存泄漏
    - CPU 限制：防止过度占用 CPU
    - 异常隔离：捕获并记录插件错误
    """
    
    def __init__(self, config: SandboxConfig = None):
        """
        初始化沙箱
        
        Args:
            config: 沙箱配置，默认使用 SandboxConfig()
        """
        self.config = config or SandboxConfig()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._active_calls = {}  # 记录活跃的调用
        logger.info(f"插件沙箱已初始化: 超时={self.config.timeout}s, "
                   f"内存限制={self.config.memory_limit_mb}MB")
    
    def execute(self, plugin_name: str, func: Callable, *args, 
                timeout: float = None, **kwargs) -> Any:
        """
        执行插件方法，带超时和异常处理
        
        Args:
            plugin_name: 插件名称（用于日志）
            func: 要执行的函数
            *args: 位置参数
            timeout: 可选的覆盖超时时间
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            PluginTimeoutError: 执行超时
            PluginExecutionError: 执行出错
            PluginResourceLimitError: 资源超限
        """
        timeout = timeout or self.config.timeout
        call_id = f"{plugin_name}_{time.time()}"
        
        logger.debug(f"沙箱执行开始: {plugin_name}, 超时={timeout}s")
        
        future = self._executor.submit(self._safe_execute, func, *args, **kwargs)
        self._active_calls[call_id] = future
        
        try:
            result = future.result(timeout=timeout)
            logger.debug(f"沙箱执行成功: {plugin_name}")
            return result
            
        except concurrent.futures.TimeoutError:
            logger.error(f"插件执行超时: {plugin_name} (>{timeout}s)")
            future.cancel()
            raise PluginTimeoutError(f"插件 {plugin_name} 执行超时（>{timeout}秒）")
            
        except Exception as e:
            logger.error(f"插件执行异常: {plugin_name} - {e}", exc_info=True)
            raise PluginExecutionError(f"插件 {plugin_name} 执行失败: {e}")
            
        finally:
            self._active_calls.pop(call_id, None)
    
    def _safe_execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        安全执行函数，设置资源限制
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        if self.config.enable_memory_limit:
            self._set_memory_limit()
        
        if self.config.enable_cpu_limit:
            self._set_cpu_limit()
        
        return func(*args, **kwargs)
    
    def _set_memory_limit(self):
        """设置内存限制"""
        try:
            limit_bytes = self.config.memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
            logger.debug(f"内存限制已设置: {self.config.memory_limit_mb}MB")
        except Exception as e:
            logger.warning(f"无法设置内存限制: {e}")
    
    def _set_cpu_limit(self):
        """设置 CPU 限制"""
        try:
            resource.setrlimit(resource.RLIMIT_CPU, 
                             (self.config.max_cpu_percent, self.config.max_cpu_percent))
            logger.debug(f"CPU 限制已设置: {self.config.max_cpu_percent}%")
        except Exception as e:
            logger.warning(f"无法设置 CPU 限制: {e}")
    
    def get_active_calls(self) -> int:
        """获取当前活跃的调用数"""
        return len(self._active_calls)
    
    def cancel_all(self):
        """取消所有活跃的调用"""
        for call_id, future in list(self._active_calls.items()):
            if not future.done():
                logger.warning(f"取消活跃调用: {call_id}")
                future.cancel()
        self._active_calls.clear()
    
    def shutdown(self, wait: bool = True):
        """
        关闭沙箱
        
        Args:
            wait: 是否等待正在执行的任务完成
        """
        self.cancel_all()
        self._executor.shutdown(wait=wait)
        logger.info("插件沙箱已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


def sandboxed(timeout: float = None, memory_limit_mb: int = None):
    """
    装饰器：为插件方法添加沙箱保护
    
    Args:
        timeout: 超时时间（秒）
        memory_limit_mb: 内存限制（MB）
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _default_sandbox
            
            config = SandboxConfig(
                timeout=timeout or 30.0,
                memory_limit_mb=memory_limit_mb or 512
            )
            sandbox = PluginSandbox(config)
            
            try:
                return sandbox.execute(
                    plugin_name=getattr(func, '__self__', func).__class__.__name__,
                    func=func,
                    *args,
                    **kwargs
                )
            finally:
                sandbox.shutdown()
        
        return wrapper
    return decorator


# 全局默认沙箱实例
_default_sandbox: Optional[PluginSandbox] = None


def get_default_sandbox() -> PluginSandbox:
    """获取全局默认沙箱实例"""
    global _default_sandbox
    if _default_sandbox is None:
        _default_sandbox = PluginSandbox()
    return _default_sandbox


def set_default_sandbox(sandbox: PluginSandbox):
    """设置全局默认沙箱实例"""
    global _default_sandbox
    if _default_sandbox is not None:
        _default_sandbox.shutdown()
    _default_sandbox = sandbox
