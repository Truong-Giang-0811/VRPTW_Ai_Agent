from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connect_db import get_async_db
from app.controller.route_plan import route_plan_crud
from app.schemas.route_plan import RoutePlanCreate, RoutePlanUpdate, RoutePlanRead
from app.api.common import list_items, get_item, create_item, update_item, delete_item

router = APIRouter(prefix="/api/route-plans", tags=["Route Plans"])


@router.get("/", response_model=list[RoutePlanRead])
async def list_route_plans(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_async_db)):
    return await list_items(route_plan_crud, db, skip, limit)


@router.get("/{item_id}", response_model=RoutePlanRead)
async def get_route_plan(item_id: int, db: AsyncSession = Depends(get_async_db)):
    return await get_item(route_plan_crud, db, item_id)


@router.post("/", response_model=RoutePlanRead, status_code=status.HTTP_201_CREATED)
async def create_route_plan(data: RoutePlanCreate, db: AsyncSession = Depends(get_async_db)):
    return await create_item(route_plan_crud, db, data.model_dump())


@router.patch("/{item_id}", response_model=RoutePlanRead)
async def update_route_plan(item_id: int, data: RoutePlanUpdate, db: AsyncSession = Depends(get_async_db)):
    return await update_item(route_plan_crud, db, item_id, data.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route_plan(item_id: int, db: AsyncSession = Depends(get_async_db)):
    await delete_item(route_plan_crud, db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
