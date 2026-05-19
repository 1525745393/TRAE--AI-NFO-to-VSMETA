# API v1 - 系统接口
"""
系统接口 - 健康检查、状态等
"""

from fastapi import APIRouter, HTTPException
from ..core import (
    success_response,
    NotFoundError,
)

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return success_response(
        data={"status": "healthy", "service": "nfo-vsmeta-server"},
        message="服务运行正常"
    )


@router.get("/status")
async def get_status():
    """获取系统状态"""
    import psutil
    return success_response(
        data={
            "memory_usage": psutil.virtual_memory().percent,
            "cpu_usage": psutil.cpu_percent(),
        }
    )


@router.get("/info")
async def get_info():
    """获取服务信息"""
    return success_response(
        data={
            "app_name": "NFO to VSMETA Server",
            "app_version": "1.0",
            "api_version": "v1"
        }
    )
