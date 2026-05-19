#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统扩展测试
增强插件系统的测试覆盖率
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from plugins.plugin_circuit_breaker import (
        CircuitState, CircuitBreaker, CircuitBreakerError
    )
    from plugins.plugin_event_bus import (
        EventBus, Event, PluginEvent
    )
    from plugins.plugin_metrics import (
        MetricsCollector, MetricType
    )
except ImportError as e:
    import pytest
    pytest.skip(f"插件未安装: {e}", allow_module_level=True)


class TestCircuitBreaker:
    """测试熔断器"""

    def test_initial_state(self):
        """测试初始状态"""
        breaker = CircuitBreaker(failure_threshold=3)
        assert breaker.state == CircuitState.CLOSED

    def test_failure_threshold(self):
        """测试失败阈值"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        assert breaker.failure_count == 0
        breaker.record_failure()
        assert breaker.failure_count == 1
        
        breaker.record_failure()
        assert breaker.failure_count == 2
        assert breaker.state == CircuitState.OPEN

    def test_recovery_timeout(self):
        """测试恢复超时"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        time.sleep(1.1)
        assert breaker.state == CircuitState.HALF_OPEN

    def test_record_success(self):
        """测试记录成功"""
        breaker = CircuitBreaker(failure_threshold=2)
        
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        time.sleep(0.1)
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_call_success(self):
        """测试调用成功"""
        breaker = CircuitBreaker()
        
        def success_func():
            return "success"
        
        result = breaker.call(success_func)
        assert result == "success"

    def test_call_failure(self):
        """测试调用失败"""
        breaker = CircuitBreaker(failure_threshold=1)
        
        def fail_func():
            raise ValueError("test error")
        
        try:
            breaker.call(fail_func)
            assert False, "应该抛出异常"
        except ValueError:
            pass
        
        assert breaker.state == CircuitState.OPEN

    def test_half_open_to_open(self):
        """测试半开到打开状态"""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        time.sleep(0.15)
        assert breaker.state == CircuitState.HALF_OPEN
        
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN


class TestEventBus:
    """测试事件总线"""

    def test_initialization(self):
        """测试初始化"""
        bus = EventBus()
        assert bus._subscribers == {}
        assert bus._event_history == []

    def test_subscribe(self):
        """测试订阅"""
        bus = EventBus()
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        bus.subscribe("test_event", handler)
        assert "test_event" in bus._subscribers

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EventBus()
        
        def handler(event):
            pass
        
        bus.subscribe("test_event", handler)
        bus.unsubscribe("test_event", handler)
        
        assert "test_event" not in bus._subscribers

    def test_publish(self):
        """测试发布事件"""
        bus = EventBus()
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        bus.subscribe("test_event", handler)
        bus.publish("test_event", {"data": "test"})
        
        assert len(received_events) == 1
        assert received_events[0]["data"] == "test"

    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        bus = EventBus()
        received1 = []
        received2 = []
        
        def handler1(event):
            received1.append(event)
        
        def handler2(event):
            received2.append(event)
        
        bus.subscribe("test_event", handler1)
        bus.subscribe("test_event", handler2)
        bus.publish("test_event", {"value": 123})
        
        assert len(received1) == 1
        assert len(received2) == 1

    def test_event_history(self):
        """测试事件历史"""
        bus = EventBus()
        
        bus.publish("event1", {"num": 1})
        bus.publish("event2", {"num": 2})
        
        assert len(bus._event_history) == 2

    def test_clear_history(self):
        """测试清空历史"""
        bus = EventBus()
        
        bus.publish("event1", {})
        bus.publish("event2", {})
        assert len(bus._event_history) == 2
        
        bus.clear_history()
        assert len(bus._event_history) == 0


class TestMetricsCollector:
    """测试指标收集器"""

    def test_initialization(self):
        """测试初始化"""
        collector = MetricsCollector()
        assert collector._metrics == {}

    def test_increment_counter(self):
        """测试计数器增加"""
        collector = MetricsCollector()
        collector.increment("requests", 1)
        collector.increment("requests", 1)
        
        assert collector.get_metric("requests") == 2

    def test_record_gauge(self):
        """测试仪表记录"""
        collector = MetricsCollector()
        collector.record_gauge("memory_usage", 1024)
        
        assert collector.get_metric("memory_usage") == 1024

    def test_record_histogram(self):
        """测试直方图记录"""
        collector = MetricsCollector()
        collector.record_histogram("response_time", 100)
        collector.record_histogram("response_time", 200)
        collector.record_histogram("response_time", 300)
        
        assert collector.get_metric("response_time_count") == 3

    def test_get_all_metrics(self):
        """测试获取所有指标"""
        collector = MetricsCollector()
        collector.increment("counter1", 1)
        collector.record_gauge("gauge1", 100)
        
        metrics = collector.get_all_metrics()
        assert "counter1" in metrics
        assert "gauge1" in metrics

    def test_reset(self):
        """测试重置"""
        collector = MetricsCollector()
        collector.increment("counter", 10)
        collector.record_gauge("gauge", 100)
        
        collector.reset()
        
        assert collector.get_metric("counter") == 0
        assert collector.get_metric("gauge") == 0


class TestPluginEvent:
    """测试插件事件"""

    def test_event_creation(self):
        """测试事件创建"""
        event = Event("test_event", {"key": "value"})
        assert event.name == "test_event"
        assert event.data["key"] == "value"

    def test_event_timestamp(self):
        """测试事件时间戳"""
        event = Event("test", {})
        assert hasattr(event, 'timestamp')


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
