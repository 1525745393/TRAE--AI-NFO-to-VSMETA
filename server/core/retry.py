# Server Core - 重试机制
"""
重试机制模块
提供灵活的重试策略和装饰器
"""

import time
import random
import logging
from functools import wraps
from typing import Any, Callable, List, Tuple, Type, Optional

logger = logging.getLogger(__name__)


class RetryPolicy:
    """
    重试策略配置

    参数：
        max_attempts: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子（默认2倍递增）
        jitter: 抖动范围（0-1，随机延迟）
        retry_exceptions: 需要重试的异常类型
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: float = 0.1,
        retry_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions or [Exception]

    def calculate_delay(self, attempt: int) -> float:
        """计算第n次重试的延迟"""
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay)

        # 添加抖动
        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)

        return delay

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_attempts:
            return False
        return any(isinstance(exception, exc_type) for exc_type in self.retry_exceptions)


def retry(
    policy: Optional[RetryPolicy] = None,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.1,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
):
    """
    重试装饰器

    参数：
        policy: 预定义的重试策略
        max_attempts: 最大重试次数
        initial_delay: 初始延迟
        max_delay: 最大延迟
        backoff_factor: 退避因子
        jitter: 抖动范围
        retry_exceptions: 需要重试的异常类型
        on_retry: 重试回调函数 (attempt, exception, delay)
    """
    if policy is None:
        policy = RetryPolicy(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
            jitter=jitter,
            retry_exceptions=retry_exceptions
        )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not policy.should_retry(attempt, e):
                        logger.error(f"函数 {func.__name__} 执行失败，已达到最大重试次数")
                        raise

                    delay = policy.calculate_delay(attempt)
                    logger.warning(
                        f"函数 {func.__name__} 执行失败，第 {attempt} 次重试，"
                        f"等待 {delay:.2f} 秒后重试..."
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    time.sleep(delay)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not policy.should_retry(attempt, e):
                        logger.error(f"函数 {func.__name__} 执行失败，已达到最大重试次数")
                        raise

                    delay = policy.calculate_delay(attempt)
                    logger.warning(
                        f"函数 {func.__name__} 执行失败，第 {attempt} 次重试，"
                        f"等待 {delay:.2f} 秒后重试..."
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    time.sleep(delay)

            raise last_exception

        # 判断函数是否是异步函数
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 预定义策略
DEFAULT_RETRY = RetryPolicy(max_attempts=3, initial_delay=1.0)
NETWORK_RETRY = RetryPolicy(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=10.0,
    retry_exceptions=[ConnectionError, TimeoutError, IOError]
)
DATABASE_RETRY = RetryPolicy(
    max_attempts=3,
    initial_delay=2.0,
    max_delay=15.0,
    backoff_factor=1.5
)
FILE_RETRY = RetryPolicy(
    max_attempts=2,
    initial_delay=0.1,
    max_delay=1.0
)
