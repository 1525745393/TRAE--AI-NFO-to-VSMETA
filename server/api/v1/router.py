# API v1 - 路由聚合
"""
API v1 路由聚合模块
"""

from fastapi import APIRouter

from . import converter, system, config

router = APIRouter(prefix="/v1")

router.include_router(system.router, prefix="/system", tags=["系统"])
router.include_router(converter.router, prefix="/converter", tags=["转换"])
router.include_router(config.router, prefix="/config", tags=["配置"])
