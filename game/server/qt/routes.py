from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from game import Game
from ..dependencies import GameContext, QtCallbacks, QtContext
from ..supplyroutes.models import interdiction_target_for_route_id

router: APIRouter = APIRouter(prefix="/qt")


@router.post(
    "/create-package/front-line/{front_line_id}",
    operation_id="open_new_front_line_package_dialog",
    status_code=status.HTTP_200_OK,
)
def new_front_line_package(
    front_line_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.create_new_package(game.db.front_lines.get(front_line_id))


@router.post(
    "/create-package/tgo/{tgo_id}",
    operation_id="open_new_tgo_package_dialog",
    status_code=status.HTTP_200_OK,
)
def new_tgo_package(
    tgo_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.create_new_package(game.db.tgos.get(tgo_id))


@router.post(
    "/info/tgo/{tgo_id}",
    operation_id="open_tgo_info_dialog",
    status_code=status.HTTP_200_OK,
)
def show_tgo_info(
    tgo_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.show_tgo_info(game.db.tgos.get(tgo_id))


@router.post(
    "/create-package/control-point/{cp_id}",
    operation_id="open_new_control_point_package_dialog",
    status_code=status.HTTP_200_OK,
)
def new_cp_package(
    cp_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    qt.create_new_package(cp)


@router.post(
    "/create-package/supply-route/{route_id}",
    operation_id="open_new_supply_route_package_dialog",
    status_code=status.HTTP_200_OK,
)
def new_supply_route_package(
    route_id: str,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    """Right-clicking an enemy supply route frags an interdiction package (an Armed
    Recon corridor) against the road's enemy end -- the convoy's source/destination."""
    target = interdiction_target_for_route_id(game, route_id)
    if target is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"No interdictable enemy control point on supply route {route_id}",
        )
    # Interdiction frag: opens the package dialog pre-selected on Armed Recon.
    qt.create_new_interdiction_package(target)


@router.post(
    "/select-flight/{flight_id}",
    operation_id="select_flight",
    status_code=status.HTTP_200_OK,
)
def select_flight(
    flight_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    flight = game.db.flights.get(flight_id)
    if flight is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no flight with ID {flight_id}",
        )
    qt.select_flight(flight)


class PlaceUnitGroupRequest(BaseModel):
    lat: float
    lng: float


@router.post(
    "/place-unit-group",
    operation_id="open_place_unit_group_dialog",
    status_code=status.HTTP_200_OK,
)
def open_place_unit_group_dialog(
    request: PlaceUnitGroupRequest,
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    qt.open_place_unit_group_dialog(request.lat, request.lng)


@router.post(
    "/info/control-point/{cp_id}",
    operation_id="open_control_point_info_dialog",
    status_code=status.HTTP_200_OK,
)
def show_control_point_info(
    cp_id: UUID,
    game: Game = Depends(GameContext.require),
    qt: QtCallbacks = Depends(QtContext.get),
) -> None:
    cp = game.theater.find_control_point_by_id(cp_id)
    if cp is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Game has no control point with ID {cp_id}",
        )
    qt.show_control_point_info(cp)
