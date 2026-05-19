#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件熔断器模块
实现熔断器模式，防止插件故障扩散
"""

import time
import logging
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
from functools import wraps

logger = logging.getLogger('plugin_circuit_breaker')


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 关闭状态，正常工作
    OPEN = "open"  # 打开状态，拒绝调用
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


class CircuitOpenError(Exception):
    """熔断器打开异常"""
    pass


class CircuitFailureError(Exception):
    """熔断器记录失败异常"""
    pass


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5  # 失败次数阈值，触发熔断
    success_threshold: int = 3  # 成功次数阈值，半开转关闭
    recovery_timeout: float = 60.0  # 恢复超时时间（秒）
    half_open_max_calls: int = 3  # 半开状态最大尝试次数
    failure_rate_threshold: float = 0.5  # 失败率阈值（50%）
    window_size: int = 100  # 滑动窗口大小


@dataclass
class CircuitMetrics:
    """熔断器指标"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    open_time: Optional[float] = None
    half_open_calls: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    @property
    def failure_rate(self) -> float:
        return 1.0 - self.success_rate
    
    @property
    def current_state_duration(self) -> Optional[float]:
        if self.open_time is None:
            return None
        return time.time() - self.open_time


class PluginCircuitBreaker:
    """
    插件熔断器
    
    实现熔断器模式，用于防止插件故障影响整个系统：
    - 失败计数：连续失败超过阈值时打开熔断器
    - 自动恢复：超时后尝试半开状态
    - 状态监控：提供详细的状态和指标信息
    
    熔断器状态转换：
    CLOSED -> OPEN (失败次数超过阈值)
    OPEN -> HALF_OPEN (恢复超时)
    HALF_OPEN -> CLOSED (成功次数达标)
    HALF_OPEN -> OPEN (再次失败)
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        """
        初始化熔断器
        
        Args:
            name: 熔断器名称（通常为插件名）
            config: 熔断器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._open_time: Optional[float] = None
        self._metrics = CircuitMetrics()
        self._call_history = []  # 最近调用历史
        self._half_open_calls = 0
        
        logger.info(f"熔断器已初始化: {name}, 配置={self.config}")
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态，自动检查是否需要转换"""
        self._check_state_transition()
        return self._state
    
    @property
    def metrics(self) -> CircuitMetrics:
        """获取熔断器指标"""
        return self._metrics
    
    def _check_state_transition(self):
        """检查状态转换"""
        if self._state == CircuitState.OPEN:
            # 检查是否应该转换到半开状态
            if self._should_attempt_reset():
                self._transition_to_half_open()
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试恢复"""
        if self._last_failure_time is None:
            return False
        
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def _transition_to_half_open(self):
        """转换到半开状态"""
        logger.info(f"熔断器 '{self.name}' 转换到半开状态（恢复超时）")
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
    
    def _transition_to_open(self):
        """转换到打开状态"""
        logger.warning(f"熔断器 '{self.name}' 转换到打开状态（失败次数: {self._failure_count}）")
        self._state = CircuitState.OPEN
        self._open_time = time.time()
        self._metrics.open_time = self._open_time
    
    def _transition_to_closed(self):
        """转换到关闭状态"""
        logger.info(f"熔断器 '{self.name}' 转换到关闭状态（恢复成功）")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._open_time = None
        self._metrics.open_time = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        调用函数，受熔断器保护
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitOpenError: 熔断器打开时调用被拒绝
            Exception: 函数执行中的异常
        """
        # 检查状态
        if self.state == CircuitState.OPEN:
            self._metrics.rejected_calls += 1
            logger.debug(f"熔断器 '{self.name}' 拒绝调用（OPEN 状态）")
            raise CircuitOpenError(f"熔断器 '{self.name}' 已打开，拒绝调用")
        
        # 半开状态检查
        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                self._metrics.rejected_calls += 1
                logger.debug(f"熔断器 '{self.name}' 拒绝调用（HALF_OPEN 达到最大尝试）")
                raise CircuitOpenError(f"熔断器 '{self.name}' 半开状态已达最大尝试次数")
            self._half_open_calls += 1
            self._metrics.half_open_calls += 1
        
        # 执行调用
        self._metrics.total_calls += 1
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            self._on_success(time.time() - start_time)
            return result
            
        except Exception as e:
            self._on_failure(time.time() - start_time)
            raise
    
    def _on_success(self, duration: float):
        """记录成功调用"""
        self._metrics.successful_calls += 1
        self._metrics.last_success_time = time.time()
        self._call_history.append({'success': True, 'duration': duration, 'time': time.time()})
        
        # 保持调用历史在窗口大小内
        if len(self._call_history) > self.config.window_size:
            self._call_history = self._call_history[-self.config.window_size:]
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
                self._success_count = 0
        
        # CLOSED 状态下重置失败计数
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0
        
        logger.debug(f"熔断器 '{self.name}' 记录成功，当前状态: {self._state.value}")
    
    def _on_failure(self, duration: float):
        """记录失败调用"""
        self._metrics.failed_calls += 1
        self._metrics.last_failure_time = time.time()
        self._failure_count += 1
        self._call_history.append({'success': False, 'duration': duration, 'time': time.time()})
        
        # 保持调用历史在窗口大小内
        if len(self._call_history) > self.config.window_size:
            self._call_history = self._call_history[-self.config.window_size:]
        
        if self._state == CircuitState.HALF_OPEN:
            # 半开状态下任何失败都直接打开
            self._transition_to_open()
            self._success_count = 0
            
        elif self._state == CircuitState.CLOSED:
            # 关闭状态下，只有当失败次数达到阈值时才打开
            # 只有在调用次数足够多时，才检查失败率
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        logger.debug(f"熔断器 '{self.name}' 记录失败 ({self._failure_count})，当前状态: {self._state.value}")
    
    def record_success(self):
        """手动记录成功（用于不需要返回值的场景）"""
        self._on_success(0)
    
    def record_failure(self):
        """手动记录失败（用于不需要返回值的场景）"""
        self._on_failure(0)
    
    def reset(self):
        """重置熔断器"""
        logger.info(f"熔断器 '{self.name}' 已重置")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._open_time = None
        self._half_open_calls = 0
        self._metrics = CircuitMetrics()
        self._call_history = []
    
    def force_open(self):
        """强制打开熔断器"""
        logger.warning(f"熔断器 '{self.name}' 被强制打开")
        self._transition_to_open()
    
    def force_close(self):
        """强制关闭熔断器"""
        logger.info(f"熔断器 '{self.name}' 被强制关闭")
        self._transition_to_closed()
    
    def get_status(self) -> Dict:
        """获取熔断器状态详情"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self._failure_count,
            'success_count': self._success_count,
            'metrics': {
                'total_calls': self._metrics.total_calls,
                'successful_calls': self._metrics.successful_calls,
                'failed_calls': self._metrics.failed_calls,
                'rejected_calls': self._metrics.rejected_calls,
                'success_rate': f"{self._metrics.success_rate:.2%}",
                'failure_rate': f"{self._metrics.failure_rate:.2%}",
            },
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'success_threshold': self.config.success_threshold,
                'recovery_timeout': self.config.recovery_timeout,
            },
            'timestamps': {
                'last_failure': time.ctime(self._metrics.last_failure_time) if self._metrics.last_failure_time else None,
                'last_success': time.ctime(self._metrics.last_success_time) if self._metrics.last_success_time else None,
                'open_time': time.ctime(self._metrics.open_time) if self._metrics.open_time else None,
                'open_duration': f"{self._metrics.current_state_duration:.1f}s" if self._metrics.current_state_duration else None,
            }
        }
    
    def __str__(self) -> str:
        return f"CircuitBreaker({self.name}, state={self.state.value}, failures={self._failure_count})"


class CircuitBreakerManager:
    """
    熔断器管理器
    
    统一管理多个插件的熔断器，提供集中式的熔断器获取和管理功能。
    """
    
    def __init__(self):
        self._breakers: Dict[str, PluginCircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
    
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> PluginCircuitBreaker:
        """
        获取或创建熔断器
        
        Args:
            name: 熔断器名称
            config: 熔断器配置（仅在新创建时使用）
            
        Returns:
            PluginCircuitBreaker 实例
        """
        if name not in self._breakers:
            self._breakers[name] = PluginCircuitBreaker(
                name=name,
                config=config or self._default_config
            )
            logger.info(f"创建新熔断器: {name}")
        return self._breakers[name]
    
    def remove_breaker(self, name: str):
        """移除熔断器"""
        if name in self._breakers:
            del self._breakers[name]
            logger.info(f"移除熔断器: {name}")
    
    def reset_all(self):
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("已重置所有熔断器")
    
    def get_all_status(self) -> Dict[str, Dict]:
        """获取所有熔断器的状态"""
        return {name: breaker.get_status() for name, breaker in self._breakers.items()}
    
    def get_summary(self) -> Dict:
        """获取熔断器摘要"""
        states = {}
        for breaker in self._breakers.values():
            state = breaker.state.value
            states[state] = states.get(state, 0) + 1
        
        return {
            'total': len(self._breakers),
            'states': states,
            'total_calls': sum(b.metrics.total_calls for b in self._breakers.values()),
            'total_failures': sum(b.metrics.failed_calls for b in self._breakers.values()),
        }


def circuit_breaker(name: str = None, config: CircuitBreakerConfig = None):
    """
    装饰器：为函数添加熔断器保护
    
    Args:
        name: 熔断器名称（默认为函数名）
        config: 熔断器配置
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        breaker_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = _global_breaker_manager.get_breaker(breaker_name, config)
            return breaker.call(func, *args, **kwargs)
        
        wrapper.breaker = _global_breaker_manager.get_breaker(breaker_name, config)
        return wrapper
    
    return decorator


# 全局熔断器管理器
_global_breaker_manager = CircuitBreakerManager()


def get_breaker_manager() -> CircuitBreakerManager:
    """获取全局熔断器管理器"""
    return _global_breaker_manager
