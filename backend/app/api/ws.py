from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.db.session import get_session_factory
from app.services.pipeline_service import PipelineService, set_last_pipeline_event

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()


class PipelineNotifyBody(BaseModel):
    message: str


def _build_snapshot_payload(message: str | None = None) -> dict[str, Any]:
    if message:
        set_last_pipeline_event(message)
    db = get_session_factory()()
    try:
        snapshot = PipelineService(db).get_snapshot()
    finally:
        db.close()
    return {
        "type": "snapshot",
        "message": message,
        "data": snapshot.model_dump(mode="json"),
    }


async def broadcast_snapshot(message: str | None = None) -> None:
    if not manager._connections:
        if message:
            set_last_pipeline_event(message)
        return
    await manager.broadcast(_build_snapshot_payload(message))


@router.websocket("/ws")
async def pipeline_websocket(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json(_build_snapshot_payload())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.post("/internal/pipeline-notify")
async def pipeline_notify(body: PipelineNotifyBody) -> dict[str, str]:
    await broadcast_snapshot(body.message)
    return {"status": "ok"}
