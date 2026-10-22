from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connect_db import get_async_db
from app.controller.route_stop import route_stop_crud
from app.schemas.route_stop import RouteStopCreate, RouteStopUpdate, RouteStopRead
from app.api.common import list_items, get_item, create_item, update_item, delete_item

router = APIRouter(prefix="/api/route-stops", tags=["Route Stops"])


@router.get("/", response_model=list[RouteStopRead])
async def list_route_stops(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_async_db)):
    return await list_items(route_stop_crud, db, skip, limit)


@router.get("/{item_id}", response_model=RouteStopRead)
async def get_route_stop(item_id: int, db: AsyncSession = Depends(get_async_db)):
    return await get_item(route_stop_crud, db, item_id)


@router.post("/", response_model=RouteStopRead, status_code=status.HTTP_201_CREATED)
async def create_route_stop(data: RouteStopCreate, db: AsyncSession = Depends(get_async_db)):
    return await create_item(route_stop_crud, db, data.model_dump())


@router.patch("/{item_id}", response_model=RouteStopRead)
async def update_route_stop(item_id: int, data: RouteStopUpdate, db: AsyncSession = Depends(get_async_db)):
    return await update_item(route_stop_crud, db, item_id, data.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route_stop(item_id: int, db: AsyncSession = Depends(get_async_db)):
    await delete_item(route_stop_crud, db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
