"""WebSocket para envio de progresso em tempo real."""

import asyncio
import json
from collections import defaultdict

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class ConnectionManager:
    """Gerencia conexões WebSocket por projeto."""

    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

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

    async def send_progress(
        self,
        project_id: str,
        step: str,
        progress: int,
        message: str = "",
        status: str = "processing",
    ) -> None:
        """Envia atualização de progresso para todos os clientes do projeto."""
        data = json.dumps(
            {
                "type": "progress",
                "project_id": project_id,
                "step": step,
                "progress": progress,
                "message": message,
                "status": status,
            }
        )

        dead_connections = []
        for ws in self.connections.get(project_id, []):
            try:
                await ws.send_text(data)
            except Exception:
                dead_connections.append(ws)

        # Limpar conexões mortas
        for ws in dead_connections:
            self.disconnect(ws, project_id)

    async def broadcast_error(
        self, project_id: str, error: str
    ) -> None:
        """Envia mensagem de erro para todos os clientes do projeto."""
        await self.send_progress(
            project_id, step="error", progress=0, message=error, status="error"
        )


# Instância global
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, project_id: str) -> None:
    """Handler do endpoint WebSocket."""
    await manager.connect(websocket, project_id)
    try:
        while True:
            # Manter conexão aberta, aguardar mensagens do cliente
            data = await websocket.receive_text()
            # Clientes podem enviar "ping" para manter a conexão
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception:
        manager.disconnect(websocket, project_id)
