"""WebSocket para envio de progresso em tempo real via Redis pub/sub."""

import asyncio
import json
import time
from collections import defaultdict

import redis
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from config import settings

logger = structlog.get_logger()

# Redis client síncrono para publicar (usado pelo Celery worker)
_redis_sync = None


def get_redis_sync():
    """Retorna cliente Redis síncrono (lazy init)."""
    global _redis_sync
    if _redis_sync is None:
        _redis_sync = redis.Redis.from_url(settings.redis_url)
    return _redis_sync


def publish_progress(
    project_id: str,
    step: str,
    progress: int,
    message: str = "",
    status: str = "processing",
    eta_seconds: int | None = None,
    elapsed_seconds: int = 0,
) -> None:
    """Publica progresso via Redis (seguro para chamar de qualquer processo)."""
    data = json.dumps({
        "type": "progress",
        "project_id": project_id,
        "step": step,
        "progress": progress,
        "message": message,
        "status": status,
        "elapsed_seconds": elapsed_seconds,
        "eta_seconds": eta_seconds,
        "timestamp": time.time(),
    })
    try:
        r = get_redis_sync()
        r.publish(f"pipeline:progress:{project_id}", data)
    except Exception as e:
        logger.warning("redis_publish_erro", error=str(e))


class ConnectionManager:
    """Gerencia conexões WebSocket por projeto."""

    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._subscriber_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, project_id: str) -> None:
        """Aceita e registra uma nova conexão WebSocket."""
        await websocket.accept()
        self.connections[project_id].append(websocket)
        logger.info("ws_conectado", project_id=project_id)

    def disconnect(self, websocket: WebSocket, project_id: str) -> None:
        """Remove uma conexão WebSocket."""
        if project_id in self.connections:
            self.connections[project_id] = [
                ws for ws in self.connections[project_id] if ws != websocket
            ]
            if not self.connections[project_id]:
                del self.connections[project_id]
        logger.info("ws_desconectado", project_id=project_id)

    async def send_to_project(self, project_id: str, data: str) -> None:
        """Envia dados para todos os clientes de um projeto."""
        dead_connections = []
        for ws in self.connections.get(project_id, []):
            try:
                await ws.send_text(data)
            except Exception:
                dead_connections.append(ws)
        for ws in dead_connections:
            self.disconnect(ws, project_id)

    def start_redis_subscriber(self) -> None:
        """Inicia subscriber Redis em background para receber progresso do Celery."""
        if self._subscriber_task is None:
            self._subscriber_task = asyncio.create_task(self._redis_subscriber())

    async def _redis_subscriber(self) -> None:
        """Loop de subscriber Redis que retransmite para WebSocket."""
        import redis.asyncio as aioredis
        try:
            r = aioredis.Redis.from_url(settings.redis_url)
            pubsub = r.pubsub()
            await pubsub.psubscribe("pipeline:progress:*")
            logger.info("redis_subscriber_iniciado")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    # Extrair project_id do canal: pipeline:progress:{project_id}
                    project_id = channel.split(":")[-1]
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    await self.send_to_project(project_id, data)
        except asyncio.CancelledError:
            logger.info("redis_subscriber_cancelado")
        except Exception as e:
            logger.error("redis_subscriber_erro", error=str(e))
            # Retry after delay
            await asyncio.sleep(5)
            self._subscriber_task = None
            self.start_redis_subscriber()


# Instância global
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, project_id: str) -> None:
    """Handler do endpoint WebSocket."""
    await manager.connect(websocket, project_id)
    # Garantir que o subscriber Redis está rodando
    manager.start_redis_subscriber()
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception:
        manager.disconnect(websocket, project_id)
