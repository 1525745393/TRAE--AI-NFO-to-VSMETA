#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件事件总线模块
实现插件间的松耦合通信机制
"""

import time
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading
import json

logger = logging.getLogger('plugin_event_bus')


class EventType(Enum):
    """预定义事件类型"""
    PLUGIN_REGISTERED = "plugin.registered"
    PLUGIN_UNREGISTERED = "plugin.unregistered"
    PLUGIN_ERROR = "plugin.error"
    PLUGIN_METRICS_UPDATED = "plugin.metrics_updated"
    CONVERSION_STARTED = "conversion.started"
    CONVERSION_FINISHED = "conversion.finished"
    FILE_PROCESSING_START = "file.processing_start"
    FILE_PROCESSING_SUCCESS = "file.processing_success"
    FILE_PROCESSING_FAILURE = "file.processing_failure"
    METADATA_PARSED = "metadata.parsed"
    METADATA_ENHANCED = "metadata.enhanced"
    VSMETA_GENERATED = "vsmeta.generated"
    CONFIG_CHANGED = "config.changed"
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"


@dataclass
class Event:
    """事件对象"""
    type: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    correlation_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def __str__(self) -> str:
        time_str = datetime.fromtimestamp(self.timestamp).isoformat()
        return f"Event({self.type}, source={self.source}, time={time_str})"


@dataclass
class EventSubscription:
    """事件订阅"""
    callback: Callable[[Event], None]
    event_type: str
    source_filter: Optional[str] = None
    async_handler: bool = False
    priority: int = 0


class EventBusError(Exception):
    """事件总线错误"""
    pass


class EventBus:
    """
    插件事件总线
    
    实现发布-订阅模式，支持插件间的松耦合通信：
    - 同步/异步事件处理
    - 事件过滤和路由
    - 事件历史记录
    - 死信队列（失败事件处理）
    - 事件相关性追踪
    
    使用方式:
        # 订阅事件
        def on_metadata_parsed(event):
            print(f"元数据已解析: {event.data}")
        
        event_bus.subscribe(EventType.METADATA_PARSED, on_metadata_parsed)
        
        # 发布事件
        event_bus.publish(EventType.METADATA_PARSED, metadata, source="my_plugin")
    """
    
    def __init__(self, max_history: int = 1000, max_retries: int = 3):
        """
        初始化事件总线
        
        Args:
            max_history: 最大历史记录数
            max_retries: 事件处理失败时的最大重试次数
        """
        self._subscriptions: Dict[str, List[EventSubscription]] = {}
        self._event_history: List[Event] = []
        self._max_history = max_history
        self._max_retries = max_retries
        self._dead_letter_queue: List[Event] = []  # 死信队列
        self._lock = threading.RLock()
        self._wildcard_subscriptions: List[EventSubscription] = []  # 通配符订阅
        self._event_counters: Dict[str, int] = {}  # 事件计数
        self._correlation_counter = 0
        
        logger.info(f"事件总线已初始化，最大历史记录: {max_history}")
    
    def subscribe(self, event_type: str, callback: Callable[[Event], None],
                 source_filter: str = None, priority: int = 0, 
                 async_handler: bool = False) -> EventSubscription:
        """
        订阅事件
        
        Args:
            event_type: 事件类型（支持 * 通配符）
            callback: 回调函数，接收 Event 对象
            source_filter: 事件源过滤器
            priority: 优先级（数字越大越先执行）
            async_handler: 是否异步处理
            
        Returns:
            EventSubscription 订阅对象
        """
        if not callable(callback):
            raise EventBusError("回调函数必须是可调用的")
        
        subscription = EventSubscription(
            callback=callback,
            event_type=event_type,
            source_filter=source_filter,
            async_handler=async_handler,
            priority=priority
        )
        
        with self._lock:
            if '*' in event_type:
                self._wildcard_subscriptions.append(subscription)
                self._wildcard_subscriptions.sort(key=lambda s: -s.priority)
            else:
                if event_type not in self._subscriptions:
                    self._subscriptions[event_type] = []
                self._subscriptions[event_type].append(subscription)
                self._subscriptions[event_type].sort(key=lambda s: -s.priority)
        
        logger.debug(f"已订阅事件: {event_type}, 优先级: {priority}")
        return subscription
    
    def unsubscribe(self, subscription: EventSubscription):
        """
        取消订阅
        
        Args:
            subscription: 要取消的订阅对象
        """
        with self._lock:
            if '*' in subscription.event_type:
                if subscription in self._wildcard_subscriptions:
                    self._wildcard_subscriptions.remove(subscription)
            else:
                if subscription.event_type in self._subscriptions:
                    if subscription in self._subscriptions[subscription.event_type]:
                        self._subscriptions[subscription.event_type].remove(subscription)
        
        logger.debug(f"已取消订阅: {subscription.event_type}")
    
    def publish(self, event_type: str, data: Any, source: str = "unknown",
               correlation_id: str = None, metadata: Dict = None, **kwargs) -> Event:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件源（插件名）
            correlation_id: 关联 ID（用于追踪相关事件）
            metadata: 附加元数据
            **kwargs: 其他事件属性
            
        Returns:
            发布的 Event 对象
        """
        event = Event(
            type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id or self._generate_correlation_id(),
            metadata=metadata or kwargs
        )
        
        # 更新计数器
        self._event_counters[event_type] = self._event_counters.get(event_type, 0) + 1
        
        # 添加到历史
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
        
        # 查找匹配的订阅
        handlers = self._find_matching_subscriptions(event_type, source)
        
        if not handlers:
            logger.debug(f"事件无订阅者: {event}")
            return event
        
        # 异步处理
        if any(h.async_handler for h in handlers):
            thread = threading.Thread(
                target=self._dispatch_event,
                args=(event, handlers),
                daemon=True
            )
            thread.start()
        else:
            self._dispatch_event(event, handlers)
        
        logger.debug(f"事件已发布: {event}, {len(handlers)} 个处理器")
        return event
    
    def _find_matching_subscriptions(self, event_type: str, source: str) -> List[EventSubscription]:
        """查找匹配事件类型的订阅"""
        handlers = []
        
        # 精确匹配
        if event_type in self._subscriptions:
            for sub in self._subscriptions[event_type]:
                if sub.source_filter is None or sub.source_filter == source:
                    handlers.append(sub)
        
        # 通配符匹配
        for sub in self._wildcard_subscriptions:
            if self._match_wildcard(event_type, sub.event_type):
                if sub.source_filter is None or sub.source_filter == source:
                    handlers.append(sub)
        
        return sorted(handlers, key=lambda h: -h.priority)
    
    def _match_wildcard(self, event_type: str, pattern: str) -> bool:
        """匹配通配符模式"""
        import re
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(f'^{regex_pattern}$', event_type))
    
    def _dispatch_event(self, event: Event, handlers: List[EventSubscription]):
        """分发事件到处理器"""
        for subscription in handlers:
            try:
                subscription.callback(event)
            except Exception as e:
                logger.error(f"事件处理器执行失败: {subscription.event_type}, 错误: {e}", exc_info=True)
                self._handle_failed_event(event, subscription, e)
    
    def _handle_failed_event(self, event: Event, subscription: EventSubscription, error: Exception):
        """处理失败的事件"""
        retry_count = event.metadata.get('_retry_count', 0)
        
        if retry_count < self._max_retries:
            event.metadata['_retry_count'] = retry_count + 1
            logger.warning(f"重试事件: {event.type}, 重试 {retry_count + 1}/{self._max_retries}")
            time.sleep(0.1 * (retry_count + 1))  # 指数退避
            self._dispatch_event(event, [subscription])
        else:
            logger.error(f"事件处理最终失败，加入死信队列: {event.type}")
            self._dead_letter_queue.append(event)
            if len(self._dead_letter_queue) > 100:
                self._dead_letter_queue = self._dead_letter_queue[-100:]
    
    def _generate_correlation_id(self) -> str:
        """生成关联 ID"""
        self._correlation_counter += 1
        return f"{int(time.time() * 1000)}-{self._correlation_counter}"
    
    def get_event_history(self, event_type: str = None, source: str = None,
                          limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        Args:
            event_type: 事件类型过滤
            source: 事件源过滤
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        with self._lock:
            events = self._event_history
            
            if event_type:
                events = [e for e in events if e.type == event_type]
            
            if source:
                events = [e for e in events if e.source == source]
            
            return events[-limit:]
    
    def get_dead_letter_queue(self) -> List[Event]:
        """获取死信队列"""
        return self._dead_letter_queue.copy()
    
    def replay_dead_letter(self, event: Event) -> bool:
        """
        重放死信事件
        
        Args:
            event: 要重放的事件
            
        Returns:
            是否成功重放
        """
        handlers = self._find_matching_subscriptions(event.type, event.source)
        
        if not handlers:
            logger.warning(f"无法重放死信，无匹配的处理器: {event.type}")
            return False
        
        try:
            event.metadata['_retry_count'] = 0
            self._dispatch_event(event, handlers)
            self._dead_letter_queue.remove(event)
            logger.info(f"成功重放死信: {event}")
            return True
        except Exception as e:
            logger.error(f"重放死信失败: {e}")
            return False
    
    def clear_dead_letter_queue(self):
        """清空死信队列"""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        logger.info(f"已清空死信队列，共 {count} 条")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取事件统计信息"""
        with self._lock:
            return {
                'total_events': len(self._event_history),
                'total_subscriptions': (
                    sum(len(subs) for subs in self._subscriptions.values()) +
                    len(self._wildcard_subscriptions)
                ),
                'event_type_counts': self._event_counters.copy(),
                'dead_letter_count': len(self._dead_letter_queue),
                'event_types': list(self._subscriptions.keys()),
            }
    
    def wait_for_event(self, event_type: str, timeout: float = 10.0) -> Optional[Event]:
        """
        等待特定事件
        
        Args:
            event_type: 事件类型
            timeout: 超时时间（秒）
            
        Returns:
            事件对象或 None（超时）
        """
        result = []
        event = threading.Event()
        
        def handler(e):
            result.append(e)
            event.set()
        
        subscription = self.subscribe(event_type, handler)
        
        try:
            event.wait(timeout=timeout)
            return result[0] if result else None
        finally:
            self.unsubscribe(subscription)
    
    def export_events(self, filepath: str, event_type: str = None,
                     start_time: float = None, end_time: float = None):
        """
        导出事件到 JSON 文件
        
        Args:
            filepath: 导出文件路径
            event_type: 事件类型过滤
            start_time: 开始时间戳
            end_time: 结束时间戳
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        data = {
            'events': [
                {
                    'type': e.type,
                    'data': str(e.data) if not isinstance(e.data, (dict, list, str, int, float, bool, type(None))) else e.data,
                    'timestamp': e.timestamp,
                    'datetime': datetime.fromtimestamp(e.timestamp).isoformat(),
                    'source': e.source,
                    'correlation_id': e.correlation_id,
                    'metadata': e.metadata,
                }
                for e in events
            ],
            'statistics': self.get_statistics(),
            'export_time': datetime.now().isoformat(),
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"事件已导出到: {filepath}, 共 {len(events)} 条")


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def publish(event_type: str, data: Any, source: str = "unknown", **kwargs) -> Event:
    """
    发布事件的便捷函数
    
    Args:
        event_type: 事件类型
        data: 事件数据
        source: 事件源
        **kwargs: 其他参数
        
    Returns:
        Event 对象
    """
    return get_event_bus().publish(event_type, data, source, **kwargs)


def subscribe(event_type: str, callback: Callable[[Event], None], **kwargs) -> EventSubscription:
    """
    订阅事件的便捷函数
    
    Args:
        event_type: 事件类型
        callback: 回调函数
        **kwargs: 其他参数
        
    Returns:
        EventSubscription 订阅对象
    """
    return get_event_bus().subscribe(event_type, callback, **kwargs)


def unsubscribe(subscription: EventSubscription):
    """
    取消订阅的便捷函数
    
    Args:
        subscription: 订阅对象
    """
    get_event_bus().unsubscribe(subscription)
