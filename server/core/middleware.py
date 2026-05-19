# Server Core - 中间件
"""
中间件模块
提供请求响应日志、CORS、异常处理等中间件
"""

import time
import logging
from typing import Callable, Dict, Any, Optional

from .errors import ServerError, error_response, InternalServerError

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware:
    """请求日志中间件"""

    def __init__(self):
        pass

    def before_request(self, request_id: str, method: str, path: str):
        """请求前处理"""
        self.start_time = time.time()
        logger.info(f"[{request_id}] {method} {path} - 开始处理")

    def after_request(self, request_id: str, method: str, path: str, status_code: int):
        """请求后处理"""
        duration = (time.time() - self.start_time) * 1000
        logger.info(
            f"[{request_id}] {method} {path} - 完成 ({status_code})"
            f"耗时 {duration:.2f}ms"
        )


class CORSHandler:
    """CORS处理"""

    def __init__(self, origins: Optional[list] = None):
        self.allowed_origins = origins or ["*"]

    def add_cors_headers(self, response, request_origin: Optional[str] = None):
        """添加CORS头部"""
        if request_origin and request_origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = request_origin
        elif "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers.update({
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Expose-Headers": "X-Total-Count",
            "Access-Control-Max-Age": "86400"
        })
        return response


class ExceptionHandler:
    """全局异常处理"""

    @staticmethod
    def handle_exception(exc: Exception) -> tuple[dict, int]:
        """处理异常并返回响应"""

        if isinstance(exc, ServerError):
            logger.error(f"服务器错误: {exc.code} - {exc.message}")
            return error_response(exc), exc.status_code

        logger.exception(f"未捕获的异常: {str(exc)}")
        internal_error = InternalServerError()
        return error_response(internal_error), internal_error.status_code


def create_request_id() -> str:
    """创建请求ID"""
    import uuid
    return str(uuid.uuid4())[:8]
