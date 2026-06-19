import asyncio

from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder

from .eventstream import EventStream
from .models import GameUpdateEventsJs
from .. import GameContext

router: APIRouter = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def shutdown(self) -> None:
        connections = list(self.active_connections)
        self.active_connections.clear()
        if connections:
            await asyncio.gather(
                *(connection.close() for connection in connections),
                return_exceptions=True,
            )

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, events: GameUpdateEventsJs) -> None:
        connections = list(self.active_connections)
        if not connections:
            return
        results = await asyncio.gather(
            *(
                connection.send_json(jsonable_encoder(events))
                for connection in connections
            ),
            return_exceptions=True,
        )
        for connection, result in zip(connections, results):
            if isinstance(result, BaseException):
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/eventstream")
async def event_stream(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            if not (events := await EventStream.get()).empty:
                if events.shutting_down:
                    await manager.shutdown()
                    return

                await manager.broadcast(
                    GameUpdateEventsJs.from_events(events, GameContext.get())
                )
    finally:
        manager.disconnect(websocket)
