# Server Core - 配置
"""
服务器配置管理
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    workers: int = 1

    # 通用
    app_name: str = "NFO to VSMETA Server"
    app_version: str = "1.0"

    # API
    api_prefix: str = "/api"
    api_v1_prefix: str = "/api/v1"

    # WebSocket
    ws_enabled: bool = True
    ws_path: str = "/ws"
    ws_ping_interval: float = 30.0

    # CORS
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # 日志
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # 安全
    secret_key: str = "dev-secret-key-change-in-production"

    def to_dict(self):
        """转换为字典"""
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "workers": self.workers,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "api_prefix": self.api_prefix,
            "ws_enabled": self.ws_enabled,
        }
