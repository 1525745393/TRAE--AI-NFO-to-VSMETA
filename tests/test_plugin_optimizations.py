#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统优化模块测试
验证所有新增功能
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPluginSandbox:
    """测试插件沙箱"""

    def test_sandbox_execution_success(self):
        """测试正常执行"""
        from plugins.plugin_sandbox import PluginSandbox, SandboxConfig
        
        sandbox = PluginSandbox(SandboxConfig(timeout=5.0))
        
        def sample_func(x, y):
            return x + y
        
        result = sandbox.execute("test_plugin", sample_func, 2, 3)
        assert result == 5
        
        sandbox.shutdown()

    def test_sandbox_timeout(self):
        """测试超时控制"""
        from plugins.plugin_sandbox import PluginSandbox, SandboxConfig, PluginTimeoutError
        
        sandbox = PluginSandbox(SandboxConfig(timeout=0.5))
        
        def slow_func():
            time.sleep(2)
            return "done"
        
        with pytest.raises(PluginTimeoutError):
            sandbox.execute("slow_plugin", slow_func, timeout=0.5)
        
        sandbox.shutdown()

    def test_sandbox_exception(self):
        """测试异常捕获"""
        from plugins.plugin_sandbox import PluginSandbox, SandboxConfig, PluginExecutionError
        
        sandbox = PluginSandbox(SandboxConfig())
        
        def failing_func():
            raise ValueError("测试错误")
        
        with pytest.raises(PluginExecutionError):
            sandbox.execute("failing_plugin", failing_func)
        
        sandbox.shutdown()


class TestConfigValidator:
    """测试配置验证器"""

    def test_basic_validation(self):
        """测试基本验证"""
        from plugins.plugin_config_validator import ConfigValidator, ConfigSchemaItem, ConfigType
        
        validator = ConfigValidator()
        validator.add_schema_item("timeout", ConfigSchemaItem(
            type=ConfigType.FLOAT,
            default=30.0,
            min_value=0.1,
            max_value=3600.0
        ))
        
        # 有效配置
        result = validator.validate({"timeout": 60.0})
        assert result.valid
        
        # 类型错误
        result = validator.validate({"timeout": "not_a_number"})
        assert not result.valid
        assert "类型错误" in str(result)

    def test_range_validation(self):
        """测试范围验证"""
        from plugins.plugin_config_validator import ConfigValidator, ConfigSchemaItem, ConfigType
        
        validator = ConfigValidator()
        validator.add_schema_item("priority", ConfigSchemaItem(
            type=ConfigType.INT,
            min_value=0,
            max_value=100
        ))
        
        # 超出范围
        result = validator.validate({"priority": 150})
        assert not result.valid
        assert "超过最大值" in str(result)

    def test_default_config(self):
        """测试默认配置生成"""
        from plugins.plugin_config_validator import ConfigValidator, ConfigSchemaItem, ConfigType
        
        validator = ConfigValidator()
        validator.add_schema_item("enabled", ConfigSchemaItem(
            type=ConfigType.BOOL,
            default=True
        ))
        validator.add_schema_item("count", ConfigSchemaItem(
            type=ConfigType.INT,
            default=10
        ))
        
        defaults = validator.get_default_config()
        assert defaults["enabled"] is True
        assert defaults["count"] == 10


class TestCircuitBreaker:
    """测试熔断器"""

    def test_circuit_breaker_closed_state(self):
        """测试关闭状态"""
        from plugins.plugin_circuit_breaker import PluginCircuitBreaker, CircuitBreakerConfig, CircuitState
        
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = PluginCircuitBreaker("test_breaker", config)
        
        assert breaker.state == CircuitState.CLOSED
        
        def success_func():
            return "success"
        
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.metrics.successful_calls == 1

    def test_circuit_breaker_open_on_failures(self):
        """测试失败时打开熔断器"""
        from plugins.plugin_circuit_breaker import (
            PluginCircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitOpenError
        )
        
        config = CircuitBreakerConfig(failure_threshold=2, success_threshold=1)
        breaker = PluginCircuitBreaker("test_breaker", config)
        
        def fail_func():
            raise ValueError("失败")
        
        # 触发熔断
        with pytest.raises(ValueError):
            breaker.call(fail_func)
        
        with pytest.raises(ValueError):
            breaker.call(fail_func)
        
        # 应该被熔断器拦截
        with pytest.raises(CircuitOpenError):
            breaker.call(lambda: "success")
        
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_manual_reset(self):
        """测试熔断器手动重置"""
        from plugins.plugin_circuit_breaker import (
            PluginCircuitBreaker, CircuitBreakerConfig, CircuitState
        )
        
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = PluginCircuitBreaker("test_breaker", config)
        
        def fail_func():
            raise ValueError("失败")
        
        # 触发熔断
        with pytest.raises(ValueError):
            breaker.call(fail_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # 手动重置
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        
        # 应该能正常调用
        result = breaker.call(lambda: "success")
        assert result == "success"


class TestPluginMetrics:
    """测试性能监控"""

    def test_metrics_recording(self):
        """测试指标记录"""
        from plugins.plugin_metrics import PluginMetricsCollector
        
        collector = PluginMetricsCollector()
        
        # 记录调用
        collector.record_call("test_plugin", 0.1, True)
        collector.record_call("test_plugin", 0.2, True)
        collector.record_call("test_plugin", 0.3, False)
        
        metrics = collector.get_metrics("test_plugin")
        assert metrics["call_count"] == 3
        assert metrics["success_count"] == 2
        assert metrics["failure_count"] == 1
        # 2/3 = 66.67%
        assert "66.67%" in metrics["success_rate"]

    def test_metrics_summary(self):
        """测试指标摘要"""
        from plugins.plugin_metrics import PluginMetricsCollector
        
        collector = PluginMetricsCollector()
        
        collector.record_call("plugin1", 0.1, True)
        collector.record_call("plugin2", 0.2, True)
        collector.record_call("plugin1", 0.3, False)
        
        summary = collector.get_summary()
        assert summary["total_plugins"] == 2
        assert summary["total_calls"] == 3
        assert summary["total_failures"] == 1

    def test_slowest_plugins(self):
        """测试最慢插件排序"""
        from plugins.plugin_metrics import PluginMetricsCollector
        
        collector = PluginMetricsCollector()
        
        collector.record_call("slow_plugin", 1.0, True)
        collector.record_call("fast_plugin", 0.1, True)
        
        slowest = collector.get_slowest_plugins(1)
        assert slowest[0]["name"] == "slow_plugin"


class TestEventBus:
    """测试事件总线"""

    def test_event_subscription_and_publish(self):
        """测试订阅和发布"""
        from plugins.plugin_event_bus import EventBus, Event
        
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        bus.subscribe("test.event", handler)
        bus.publish("test.event", {"data": "hello"}, source="test")
        
        assert len(received) == 1
        assert received[0].data == {"data": "hello"}
        assert received[0].source == "test"

    def test_wildcard_subscription(self):
        """测试通配符订阅"""
        from plugins.plugin_event_bus import EventBus
        
        bus = EventBus()
        received = []
        
        def handler(event):
            received.append(event)
        
        bus.subscribe("plugin.*", handler)
        bus.publish("plugin.loaded", {"status": "ok"}, source="test")
        
        assert len(received) == 1
        assert received[0].type == "plugin.loaded"

    def test_event_history(self):
        """测试事件历史"""
        from plugins.plugin_event_bus import EventBus
        
        bus = EventBus()
        
        bus.publish("test.event1", {"num": 1}, source="test")
        bus.publish("test.event2", {"num": 2}, source="test")
        bus.publish("test.event3", {"num": 3}, source="test")
        
        history = bus.get_event_history(limit=2)
        assert len(history) == 2
        assert history[-1].data["num"] == 3

    def test_statistics(self):
        """测试事件统计"""
        from plugins.plugin_event_bus import EventBus
        
        bus = EventBus()
        
        bus.subscribe("test.event", lambda e: None)
        bus.publish("test.event", {"data": 1}, source="source1")
        bus.publish("test.event", {"data": 2}, source="source2")
        
        stats = bus.get_statistics()
        assert stats["total_events"] == 2
        assert stats["total_subscriptions"] == 1


class TestPluginMarketplace:
    """测试插件市场"""

    def test_list_installed(self):
        """测试列出已安装插件"""
        from plugins.plugin_marketplace import PluginMarketplace
        
        marketplace = PluginMarketplace()
        
        installed = marketplace.list_installed()
        assert isinstance(installed, list)

    def test_categories(self):
        """测试获取分类"""
        from plugins.plugin_marketplace import PluginMarketplace
        
        marketplace = PluginMarketplace()
        
        categories = marketplace.get_categories()
        assert len(categories) >= 1
        assert all("name" in cat for cat in categories)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
