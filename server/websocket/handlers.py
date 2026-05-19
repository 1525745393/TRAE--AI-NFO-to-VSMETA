
# WebSocket 处理器

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import Dict, Any
import json
from datetime import datetime
import asyncio

from .manager import manager
from ..core import success_response


router = APIRouter()


async def handle_conversion_progress(websocket: WebSocket, client_id: str):
    try:
        while True:
            await asyncio.sleep(1)
            progress_data = {
                "type": "conversion_progress",
                "task_id": f"task_{client_id}",
                "progress": 50,
                "status": "processing",
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.send_personal_message(progress_data, client_id)
    except asyncio.CancelledError:
        pass


@router.websocket("/ws/converter")
async def websocket_converter(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    try:
        await manager.send_personal_message(
            {
                "type": "connected",
                "client_id": client_id,
                "message": "连接成功"
            },
            client_id
        )
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "start_conversion":
                await manager.send_personal_message(
                    {
                        "type": "conversion_started",
                        "task_id": data.get("task_id"),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    client_id
                )
            elif data.get("type") == "ping":
                await manager.send_personal_message(
                    {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    client_id
                )
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
        manager.disconnect(client_id)


@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    try:
        await manager.send_personal_message(
            {
                "type": "connected",
                "client_id": client_id,
                "message": "状态监控连接成功"
            },
            client_id
        )
        manager.subscribe(client_id, "system_status")
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe":
                channel = data.get("channel")
                if channel:
                    manager.subscribe(client_id, channel)
            elif data.get("type") == "unsubscribe":
                channel = data.get("channel")
                if channel:
                    manager.unsubscribe(client_id, channel)
    except WebSocketDisconnect:
        manager.disconnect(client_id)


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    try:
        await manager.send_personal_message(
            {
                "type": "connected",
                "client_id": client_id,
                "message": "日志监控连接成功"
            },
            client_id
        )
        manager.subscribe(client_id, "logs")
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

