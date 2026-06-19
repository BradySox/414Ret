import time
from collections.abc import Iterator
from contextlib import contextmanager
from threading import Thread
from typing import Optional

import uvicorn
from uvicorn import Config

from game.server import EventStream
from game.server.app import app
from game.server.settings import ServerSettings
from game.sim import GameUpdateEvents

# Upper bound (seconds) on uvicorn's graceful shutdown; without it, it can wait
# forever for the long-lived /eventstream websocket task to drain on exit.
GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 3
STARTUP_TIMEOUT_SECONDS = 10


class ServerStartupError(RuntimeError):
    pass


class Server(uvicorn.Server):
    def __init__(self, port: Optional[int]) -> None:
        settings = ServerSettings.get(port)
        super().__init__(
            Config(
                app=app,
                host=settings.server_bind_address,
                port=settings.server_port,
                # Configured explicitly with default_logging.yaml or logging.yaml.
                log_config=None,
                timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
            )
        )

    @contextmanager
    def run_in_thread(self) -> Iterator[None]:
        # This relies on undocumented behavior, but it is what the developer recommends:
        # https://github.com/encode/uvicorn/issues/742
        startup_error: BaseException | None = None

        def run_server() -> None:
            nonlocal startup_error
            try:
                self.run()
            except BaseException as ex:
                startup_error = ex

        thread = Thread(target=run_server, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
            while not self.started:
                if startup_error is not None:
                    raise ServerStartupError(
                        "Web server failed to start"
                    ) from startup_error
                if not thread.is_alive():
                    raise ServerStartupError(
                        "Web server stopped before startup completed"
                    )
                if time.monotonic() >= deadline:
                    raise ServerStartupError(
                        f"Web server did not start within {STARTUP_TIMEOUT_SECONDS} seconds"
                    )
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            if self.started:
                EventStream.put_nowait(GameUpdateEvents().shut_down())
            thread.join(timeout=GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS + 2)
            if thread.is_alive():
                # Graceful shutdown stalled anyway; force uvicorn to stop waiting
                # so the process can exit instead of hanging on join() forever.
                self.force_exit = True
                thread.join(timeout=GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS)
