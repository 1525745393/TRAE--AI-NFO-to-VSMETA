# API v1 - 配置接口
"""
配置管理接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from ...core import success_response, ValidationError

router = APIRouter()


# 数据模型
class ConfigUpdate(BaseModel):
    key: str
    value: Any


@router.get("/")
async def get_config():
    """获取配置"""
    return success_response(
        data={"config": {"example": "value"}},
        message="获取配置成功"
    )


@router.put("/")
async def update_config(update: ConfigUpdate):
    """更新配置"""
    if not update.key:
        raise ValidationError(message="配置键不能为空")

    return success_response(
        data={"key": update.key, "value": update.value},
        message="配置更新成功"
    )


@router.post("/reset")
async def reset_config():
    """重置配置"""
    return success_response(message="配置已重置为默认值")


@router.get("/schema")
async def get_config_schema():
    """获取配置Schema"""
    return success_response(
        data={
            "schema": {
                "example": {
                    "type": "string",
                    "default": "default_value",
                    "description": "示例配置项"
                }
            }
        }
    )
