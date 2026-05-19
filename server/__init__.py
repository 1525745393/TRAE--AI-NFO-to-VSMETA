# Server 架构模块入口
"""
NFO to VSMETA Server
API分层设计 + WebSocket支持
"""

from .main import create_app, app
from .core import (
    ServerConfig,
    ServerError,
    NotFoundError,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    InternalServerError,
    ConflictError,
    RateLimitError,
    RetryPolicy,
    retry,
    success_response,
    error_response
)
from .websocket import ConnectionManager

__version__ = "1.0.0"

__all__ = [
    "create_app",
    "app",
    "ServerConfig",
    "ServerError",
    "NotFoundError",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "InternalServerError",
    "ConflictError",
    "RateLimitError",
    "RetryPolicy",
    "retry",
    "success_response",
    "error_response",
    "ConnectionManager",
    "__version__"
]

