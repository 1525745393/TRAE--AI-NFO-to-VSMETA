
# WebSocket 连接管理器

import uuid
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.channel_subscribers: Dict[str, Set[str]] = {}
        self.connection_info: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -&gt; str:
        if client_id is None:
            client_id = str(uuid.uuid4())
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "client_id": client_id
        }
        return client_id

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.connection_info:
            del self.connection_info[client_id]
        for channel in list(self.channel_subscribers.keys()):
            if client_id in self.channel_subscribers[channel]:
                self.channel_subscribers[channel].remove(client_id)
                if not self.channel_subscribers[channel]:
                    del self.channel_subscribers[channel]

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except WebSocketDisconnect:
                self.disconnect(client_id)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)

    async def send_to_channel(self, channel: str, message: Dict[str, Any]):
        if channel not in self.channel_subscribers:
            return
        disconnected = []
        for client_id in self.channel_subscribers[channel]:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except WebSocketDisconnect:
                    disconnected.append(client_id)
        for client_id in disconnected:
            self.disconnect(client_id)

    def subscribe(self, client_id: str, channel: str):
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(client_id)

    def unsubscribe(self, client_id: str, channel: str):
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(client_id)
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]

    def get_active_connections_count(self) -&gt; int:
        return len(self.active_connections)

    def get_connection_info(self, client_id: str) -&gt; Optional[Dict[str, Any]]:
        return self.connection_info.get(client_id)


manager = ConnectionManager()

