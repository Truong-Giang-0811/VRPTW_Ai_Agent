from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connect_db import get_async_db
from app.controller.depot import depot_crud
from app.schemas.depot import DepotCreate, DepotUpdate, DepotRead
from app.api.common import list_items, get_item, create_item, update_item, delete_item

router = APIRouter(prefix="/api/depots", tags=["Depots"])


@router.get("/", response_model=list[DepotRead])
async def list_depots(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_async_db)):
    return await list_items(depot_crud, db, skip, limit)


@router.get("/{item_id}", response_model=DepotRead)
async def get_depot(item_id: int, db: AsyncSession = Depends(get_async_db)):
    return await get_item(depot_crud, db, item_id)


@router.post("/", response_model=DepotRead, status_code=status.HTTP_201_CREATED)
async def create_depot(data: DepotCreate, db: AsyncSession = Depends(get_async_db)):
    return await create_item(depot_crud, db, data.model_dump())


@router.patch("/{item_id}", response_model=DepotRead)
async def update_depot(item_id: int, data: DepotUpdate, db: AsyncSession = Depends(get_async_db)):
    return await update_item(depot_crud, db, item_id, data.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_depot(item_id: int, db: AsyncSession = Depends(get_async_db)):
    await delete_item(depot_crud, db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
