from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connect_db import get_async_db
from app.controller.vehicle import vehicle_crud
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleRead
from app.api.common import list_items, get_item, create_item, update_item, delete_item

router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])


@router.get("/", response_model=list[VehicleRead])
async def list_vehicles(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_async_db)):
    return await list_items(vehicle_crud, db, skip, limit)


@router.get("/{item_id}", response_model=VehicleRead)
async def get_vehicle(item_id: int, db: AsyncSession = Depends(get_async_db)):
    return await get_item(vehicle_crud, db, item_id)


@router.post("/", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(data: VehicleCreate, db: AsyncSession = Depends(get_async_db)):
    return await create_item(vehicle_crud, db, data.model_dump())


@router.patch("/{item_id}", response_model=VehicleRead)
async def update_vehicle(item_id: int, data: VehicleUpdate, db: AsyncSession = Depends(get_async_db)):
    return await update_item(vehicle_crud, db, item_id, data.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(item_id: int, db: AsyncSession = Depends(get_async_db)):
    await delete_item(vehicle_crud, db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
