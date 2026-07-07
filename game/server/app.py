from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import (
    controlpoints,
    debuggeometries,
    eventstream,
    flights,
    fogofwar,
    frontlines,
    game,
    maptiles,
    mapzones,
    navmesh,
    qt,
    supplyroutes,
    tgos,
    waypoints,
    iadsnetwork,
)
from .settings import ServerSettings

app = FastAPI()


@app.exception_handler(KeyError)
async def _key_error_as_404(request: Request, exc: KeyError) -> JSONResponse:
    """Unknown-id lookups raise KeyError, not None (Database.get,
    find_control_point_by_id), so the routes' `is None` guards never fire and a
    stale client id produced a 500 + traceback. Map them to a clean 404."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(controlpoints.router)
app.include_router(debuggeometries.router)
app.include_router(eventstream.router)
app.include_router(flights.router)
app.include_router(fogofwar.router)
app.include_router(frontlines.router)
app.include_router(game.router)
app.include_router(maptiles.router)
app.include_router(mapzones.router)
app.include_router(navmesh.router)
app.include_router(qt.router)
app.include_router(supplyroutes.router)
app.include_router(tgos.router)
app.include_router(waypoints.router)
app.include_router(iadsnetwork.router)


origins = ["file://"]
if ServerSettings.get().cors_allow_debug_server:
    origins.append("http://localhost:3000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
