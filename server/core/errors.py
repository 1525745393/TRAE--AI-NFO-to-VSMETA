# Server Core - 错误处理
"""
错误处理模块
定义服务器错误类型和异常处理机制
"""

from typing import Any, Dict, Optional


class ServerError(Exception):
    """基础服务器错误"""

    def __init__(self, message: str = "服务器错误", status_code: int = 500, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于API响应"""
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message
            }
        }


class NotFoundError(ServerError):
    """资源未找到"""

    def __init__(self, message: str = "资源未找到", code: str = "NOT_FOUND"):
        super().__init__(message, status_code=404, code=code)


class ValidationError(ServerError):
    """参数验证错误"""

    def __init__(self, message: str = "参数验证失败", errors: Optional[Dict] = None, code: str = "VALIDATION_ERROR"):
        super().__init__(message, status_code=400, code=code)
        self.errors = errors or {}

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.errors:
            result["error"]["details"] = self.errors
        return result


class UnauthorizedError(ServerError):
    """未授权访问"""

    def __init__(self, message: str = "未授权访问", code: str = "UNAUTHORIZED"):
        super().__init__(message, status_code=401, code=code)


class ForbiddenError(ServerError):
    """禁止访问"""

    def __init__(self, message: str = "禁止访问", code: str = "FORBIDDEN"):
        super().__init__(message, status_code=403, code=code)


class InternalServerError(ServerError):
    """内部服务器错误"""

    def __init__(self, message: str = "内部服务器错误", code: str = "INTERNAL_ERROR"):
        super().__init__(message, status_code=500, code=code)


class ConflictError(ServerError):
    """资源冲突"""

    def __init__(self, message: str = "资源冲突", code: str = "CONFLICT"):
        super().__init__(message, status_code=409, code=code)


class RateLimitError(ServerError):
    """速率限制"""

    def __init__(self, message: str = "请求过于频繁", code: str = "RATE_LIMITED", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429, code=code)
        self.retry_after = retry_after

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.retry_after:
            result["error"]["retry_after"] = self.retry_after
        return result


def success_response(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应"""
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response


def error_response(error: ServerError) -> Dict[str, Any]:
    """创建错误响应"""
    return error.to_dict()
