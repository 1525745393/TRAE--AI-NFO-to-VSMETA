#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件性能监控模块
收集和分析插件执行性能指标
"""

import time
import logging
import statistics
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
import json

logger = logging.getLogger('plugin_metrics')


@dataclass
class PluginMetrics:
    """插件性能指标"""
    name: str
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    call_times: List[float] = field(default_factory=list)
    error_messages: List[Dict] = field(default_factory=list)
    first_call_time: Optional[float] = None
    last_call_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    
    @property
    def avg_time(self) -> float:
        """平均执行时间（秒）"""
        return self.total_time / self.call_count if self.call_count > 0 else 0.0
    
    @property
    def avg_time_ms(self) -> float:
        """平均执行时间（毫秒）"""
        return self.avg_time * 1000
    
    @property
    def success_rate(self) -> float:
        """成功率（百分比）"""
        if self.call_count == 0:
            return 100.0
        return (self.success_count / self.call_count) * 100
    
    @property
    def failure_rate(self) -> float:
        """失败率（百分比）"""
        return 100.0 - self.success_rate
    
    @property
    def p50(self) -> float:
        """P50 延迟（秒）"""
        if len(self.call_times) < 2:
            return self.avg_time
        return statistics.median(self.call_times)
    
    @property
    def p95(self) -> float:
        """P95 延迟（秒）"""
        if len(self.call_times) < 20:
            return self.max_time
        return statistics.quantiles(self.call_times, n=20)[18]
    
    @property
    def p99(self) -> float:
        """P99 延迟（秒）"""
        if len(self.call_times) < 100:
            return self.max_time
        return statistics.quantiles(self.call_times, n=100)[98]
    
    @property
    def throughput(self) -> float:
        """吞吐量（调用/秒）"""
        if self.total_time == 0:
            return 0.0
        return self.call_count / self.total_time
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'call_count': self.call_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': f"{self.success_rate:.2f}%",
            'failure_rate': f"{self.failure_rate:.2f}%",
            'total_time': f"{self.total_time:.3f}s",
            'avg_time': f"{self.avg_time:.3f}s",
            'avg_time_ms': f"{self.avg_time_ms:.2f}ms",
            'min_time': f"{self.min_time:.3f}s",
            'max_time': f"{self.max_time:.3f}s",
            'p50': f"{self.p50:.3f}s",
            'p95': f"{self.p95:.3f}s",
            'p99': f"{self.p99:.3f}s",
            'throughput': f"{self.throughput:.2f}/s",
            'first_call': datetime.fromtimestamp(self.first_call_time).isoformat() if self.first_call_time else None,
            'last_call': datetime.fromtimestamp(self.last_call_time).isoformat() if self.last_call_time else None,
            'error_count': len(self.error_messages),
        }


class PluginMetricsCollector:
    """
    插件性能监控收集器
    
    收集和管理所有插件的性能指标，支持：
    - 调用次数统计
    - 执行时间统计（平均、P50、P95、P99）
    - 成功/失败率统计
    - 吞吐量计算
    - 历史数据保留
    """
    
    def __init__(self, max_history: int = 1000):
        """
        初始化收集器
        
        Args:
            max_history: 每个插件保留的最大历史记录数
        """
        self._metrics: Dict[str, PluginMetrics] = {}
        self._max_history = max_history
        self._call_history: List[Dict] = []  # 全局调用历史
        self._max_global_history = max_history * 10
        
        logger.info(f"性能监控收集器已初始化，最大历史记录: {max_history}")
    
    def record_call(self, plugin_name: str, duration: float, success: bool, 
                    error: Exception = None):
        """
        记录插件调用
        
        Args:
            plugin_name: 插件名称
            duration: 执行时长（秒）
            success: 是否成功
            error: 异常对象（如果有）
        """
        if plugin_name not in self._metrics:
            self._metrics[plugin_name] = PluginMetrics(name=plugin_name)
        
        m = self._metrics[plugin_name]
        m.call_count += 1
        m.total_time += duration
        m.last_call_time = time.time()
        
        if m.first_call_time is None:
            m.first_call_time = m.last_call_time
        
        if duration < m.min_time:
            m.min_time = duration
        if duration > m.max_time:
            m.max_time = duration
        
        m.call_times.append(duration)
        if len(m.call_times) > self._max_history:
            m.call_times = m.call_times[-self._max_history:]
        
        if success:
            m.success_count += 1
            m.last_success_time = time.time()
        else:
            m.failure_count += 1
            m.last_failure_time = time.time()
            
            if error is not None:
                m.error_messages.append({
                    'time': time.time(),
                    'error_type': type(error).__name__,
                    'error_message': str(error),
                })
                if len(m.error_messages) > 100:
                    m.error_messages = m.error_messages[-100:]
        
        # 全局调用历史
        self._call_history.append({
            'time': time.time(),
            'plugin_name': plugin_name,
            'duration': duration,
            'success': success,
            'error_type': type(error).__name__ if error else None,
        })
        if len(self._call_history) > self._max_global_history:
            self._call_history = self._call_history[-self._max_global_history:]
        
        logger.debug(f"记录调用: {plugin_name}, 耗时={duration:.3f}s, 成功={success}")
    
    def get_metrics(self, plugin_name: str = None) -> Dict[str, Any]:
        """
        获取性能指标
        
        Args:
            plugin_name: 插件名称（None 表示所有）
            
        Returns:
            性能指标字典
        """
        if plugin_name:
            if plugin_name not in self._metrics:
                return {}
            return self._metrics[plugin_name].to_dict()
        
        return {
            name: m.to_dict() 
            for name, m in sorted(self._metrics.items())
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self._metrics:
            return {
                'total_plugins': 0,
                'total_calls': 0,
                'total_failures': 0,
                'overall_success_rate': '100.00%',
                'total_time': '0.000s',
            }
        
        total_calls = sum(m.call_count for m in self._metrics.values())
        total_failures = sum(m.failure_count for m in self._metrics.values())
        total_time = sum(m.total_time for m in self._metrics.values())
        
        return {
            'total_plugins': len(self._metrics),
            'total_calls': total_calls,
            'total_failures': total_failures,
            'total_successes': total_calls - total_failures,
            'overall_success_rate': f"{(total_calls - total_failures) / total_calls * 100:.2f}%" if total_calls > 0 else '100.00%',
            'total_time': f"{total_time:.3f}s",
            'avg_call_time': f"{total_time / total_calls:.3f}s" if total_calls > 0 else '0.000s',
        }
    
    def get_slowest_plugins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最慢的插件列表"""
        sorted_metrics = sorted(
            self._metrics.values(),
            key=lambda m: m.total_time,
            reverse=True
        )
        return [m.to_dict() for m in sorted_metrics[:limit]]
    
    def get_most_called_plugins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取调用次数最多的插件列表"""
        sorted_metrics = sorted(
            self._metrics.values(),
            key=lambda m: m.call_count,
            reverse=True
        )
        return [m.to_dict() for m in sorted_metrics[:limit]]
    
    def get_failed_plugins(self) -> List[Dict[str, Any]]:
        """获取有失败的插件列表"""
        return [
            m.to_dict() for m in self._metrics.values()
            if m.failure_count > 0
        ]
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """获取最近的错误"""
        errors = []
        for m in self._metrics.values():
            for error in m.error_messages[-limit:]:
                errors.append({
                    'plugin_name': m.name,
                    'time': datetime.fromtimestamp(error['time']).isoformat(),
                    'error_type': error['error_type'],
                    'error_message': error['error_message'],
                })
        
        return sorted(errors, key=lambda x: x['time'], reverse=True)[:limit]
    
    def get_call_history(self, plugin_name: str = None, limit: int = 100) -> List[Dict]:
        """获取调用历史"""
        history = self._call_history
        
        if plugin_name:
            history = [h for h in history if h['plugin_name'] == plugin_name]
        
        return history[-limit:]
    
    def reset(self, plugin_name: str = None):
        """
        重置指标
        
        Args:
            plugin_name: 插件名称（None 表示所有）
        """
        if plugin_name:
            if plugin_name in self._metrics:
                self._metrics[plugin_name] = PluginMetrics(name=plugin_name)
                logger.info(f"已重置插件 '{plugin_name}' 的指标")
        else:
            self._metrics = {}
            self._call_history = []
            logger.info("已重置所有性能指标")
    
    def export_to_json(self, filepath: str):
        """导出指标到 JSON 文件"""
        data = {
            'summary': self.get_summary(),
            'metrics': self.get_metrics(),
            'slowest_plugins': self.get_slowest_plugins(),
            'most_called_plugins': self.get_most_called_plugins(),
            'failed_plugins': self.get_failed_plugins(),
            'recent_errors': self.get_recent_errors(),
            'export_time': datetime.now().isoformat(),
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"性能指标已导出到: {filepath}")
    
    def generate_report(self) -> str:
        """生成性能报告"""
        lines = [
            "=" * 70,
            "插件性能报告",
            "=" * 70,
            "",
        ]
        
        # 摘要
        summary = self.get_summary()
        lines.extend([
            "【摘要】",
            f"  总插件数: {summary['total_plugins']}",
            f"  总调用次数: {summary['total_calls']}",
            f"  总失败次数: {summary['total_failures']}",
            f"  总成功次数: {summary['total_successes']}",
            f"  整体成功率: {summary['overall_success_rate']}",
            f"  总执行时间: {summary['total_time']}",
            f"  平均调用时间: {summary['avg_call_time']}",
            "",
        ])
        
        # 最慢插件
        lines.append("【最慢的插件】")
        for i, m in enumerate(self.get_slowest_plugins(5), 1):
            lines.append(f"  {i}. {m['name']}")
            lines.append(f"     总时间: {m['total_time']}, 平均: {m['avg_time']}, P95: {m['p95']}")
        lines.append("")
        
        # 失败插件
        failed = self.get_failed_plugins()
        if failed:
            lines.append("【有失败的插件】")
            for m in failed:
                lines.append(f"  - {m['name']}: {m['failure_count']} 失败, 成功率 {m['success_rate']}")
            lines.append("")
        
        # 最近错误
        errors = self.get_recent_errors(5)
        if errors:
            lines.append("【最近错误】")
            for e in errors:
                lines.append(f"  [{e['time']}] {e['plugin_name']}")
                lines.append(f"    {e['error_type']}: {e['error_message']}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


def monitored(plugin_name: str = None):
    """
    装饰器：自动收集插件方法性能指标
    
    Args:
        plugin_name: 插件名称（默认为函数名）
        
    使用方式:
        @monitored("my_plugin")
        def my_method(self, ...):
            pass
    """
    def decorator(func: Callable) -> Callable:
        name = plugin_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration = time.time() - start_time
                _global_metrics_collector.record_call(name, duration, success, error)
        
        return wrapper
    
    return decorator


# 全局性能监控收集器实例
_global_metrics_collector = PluginMetricsCollector()


def get_metrics_collector() -> PluginMetricsCollector:
    """获取全局性能监控收集器"""
    return _global_metrics_collector


def record_plugin_call(plugin_name: str, duration: float, success: bool, 
                      error: Exception = None):
    """
    记录插件调用的便捷函数
    
    Args:
        plugin_name: 插件名称
        duration: 执行时长（秒）
        success: 是否成功
        error: 异常对象（如果有）
    """
    _global_metrics_collector.record_call(plugin_name, duration, success, error)


class PerformanceTracker:
    """
    性能跟踪上下文管理器
    
    用于手动跟踪代码块的性能。
    
    使用方式:
        with PerformanceTracker("my_operation") as tracker:
            # 执行操作
            pass
        print(f"耗时: {tracker.duration}s")
    """
    
    def __init__(self, operation_name: str, plugin_name: str = None):
        self.operation_name = operation_name
        self.plugin_name = plugin_name or "unknown"
        self.start_time = None
        self.duration = None
        self.success = False
        self.error = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        self.success = exc_type is None
        self.error = exc_val
        
        _global_metrics_collector.record_call(
            f"{self.plugin_name}.{self.operation_name}",
            self.duration,
            self.success,
            self.error
        )
