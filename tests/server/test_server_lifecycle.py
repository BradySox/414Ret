import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from game.server.eventstream.routes import ConnectionManager
from game.server.server import Server, ServerStartupError


def test_server_thread_failure_is_propagated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = Server(port=16880)
    monkeypatch.setattr(
        server, "run", MagicMock(side_effect=OSError("address already in use"))
    )

    with pytest.raises(ServerStartupError) as exc_info:
        with server.run_in_thread():
            pytest.fail("server context should not be entered")

    assert isinstance(exc_info.value.__cause__, OSError)


def test_broadcast_prunes_failed_websockets() -> None:
    manager = ConnectionManager()
    healthy = MagicMock()
    healthy.send_json = AsyncMock(return_value=None)
    failed = MagicMock()
    failed.send_json = AsyncMock(side_effect=RuntimeError("disconnected"))
    manager.active_connections = [healthy, failed]

    asyncio.run(manager.broadcast(MagicMock()))

    assert manager.active_connections == [healthy]


def test_shutdown_handles_no_connections() -> None:
    asyncio.run(ConnectionManager().shutdown())
