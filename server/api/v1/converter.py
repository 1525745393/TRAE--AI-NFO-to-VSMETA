# API v1 - 转换接口
"""
转换服务接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

from ...core import (
    success_response,
    NotFoundError,
    ValidationError,
    retry,
    NETWORK_RETRY
)

router = APIRouter()


# 数据模型
class ConvertRequest(BaseModel):
    file_path: str
    output_dir: Optional[str] = None
    overwrite: bool = False


class BatchConvertRequest(BaseModel):
    file_paths: List[str]
    output_dir: Optional[str] = None
    overwrite: bool = False


@router.post("/convert")
async def convert_single(request: ConvertRequest):
    """单个文件转换"""
    if not request.file_path:
        raise ValidationError(message="文件路径不能为空")

    try:
        result = await _perform_convert(request)
        return success_response(data=result, message="转换成功")
    except FileNotFoundError:
        raise NotFoundError(message="指定的文件不存在")


@router.post("/batch-convert")
async def batch_convert(request: BatchConvertRequest):
    """批量转换"""
    if not request.file_paths:
        raise ValidationError(message="文件列表不能为空")

    results = []
    for file_path in request.file_paths:
        try:
            result = await _perform_convert(
                ConvertRequest(file_path=file_path, output_dir=request.output_dir, overwrite=request.overwrite)
            )
            results.append({"file": file_path, "success": True, "result": result})
        except Exception as e:
            results.append({"file": file_path, "success": False, "error": str(e)})

    return success_response(
        data={"results": results, "total": len(request.file_paths)},
        message="批量转换完成"
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    # 模拟任务状态检查
    statuses = ["pending", "processing", "completed", "error"]
    import random
    return success_response(
        data={
            "task_id": task_id,
            "status": random.choice(statuses),
            "progress": random.randint(0, 100)
        }
    )


# 内部函数
@retry(policy=NETWORK_RETRY)
async def _perform_convert(request: ConvertRequest):
    """执行转换逻辑"""
    # 模拟转换过程
    await _simulate_io_operation()
    return {
        "file_path": request.file_path,
        "output_path": f"{request.file_path}.vsmeta"
    }


async def _simulate_io_operation():
    """模拟IO操作"""
    import asyncio
    await asyncio.sleep(0.5)
