from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connect_db import get_async_db
from app.controller.delivery_order import delivery_order_crud
from app.models.delivery_order import DeliveryOrder
from app.schemas.delivery_order import DeliveryOrderCreate, DeliveryOrderUpdate, DeliveryOrderRead
from app.api.common import list_items, get_item, create_item, update_item, delete_item

router = APIRouter(prefix="/api/orders", tags=["Delivery Orders"])


@router.get("/", response_model=list[DeliveryOrderRead])
async def list_orders(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_async_db)):
    return await list_items(delivery_order_crud, db, skip, limit)


@router.get("/page")
async def list_orders_page(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    delivery_date: date | None = Query(None, description="Lọc chính xác theo ngày giao trước khi phân trang"),
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None, min_length=1, max_length=150, description="Tìm mã đơn, khách hàng hoặc địa chỉ"),
    db: AsyncSession = Depends(get_async_db),
):
    """Danh sách đơn có lọc phía DB và phân trang; giữ nguyên GET /api/orders/ cũ."""
    conditions = []
    if delivery_date is not None:
        conditions.append(DeliveryOrder.delivery_date == delivery_date)
    if status_filter:
        conditions.append(DeliveryOrder.status == status_filter)
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(or_(
            DeliveryOrder.code.ilike(pattern),
            DeliveryOrder.name.ilike(pattern),
            DeliveryOrder.address.ilike(pattern),
        ))

    count_stmt = select(func.count()).select_from(DeliveryOrder)
    data_stmt = select(DeliveryOrder)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        data_stmt = data_stmt.where(*conditions)

    total = int((await db.scalar(count_stmt)) or 0)
    data_stmt = data_stmt.order_by(DeliveryOrder.delivery_date.desc(), DeliveryOrder.id.desc()).offset(skip).limit(limit)
    result = await db.scalars(data_stmt)
    return {
        "items": [DeliveryOrderRead.model_validate(item) for item in result.all()],
        "total": total,
        "skip": skip,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/{item_id}", response_model=DeliveryOrderRead)
async def get_order(item_id: int, db: AsyncSession = Depends(get_async_db)):
    return await get_item(delivery_order_crud, db, item_id)


@router.post("/", response_model=DeliveryOrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(data: DeliveryOrderCreate, db: AsyncSession = Depends(get_async_db)):
    return await create_item(delivery_order_crud, db, data.model_dump())


@router.patch("/{item_id}", response_model=DeliveryOrderRead)
async def update_order(item_id: int, data: DeliveryOrderUpdate, db: AsyncSession = Depends(get_async_db)):
    return await update_item(delivery_order_crud, db, item_id, data.model_dump(exclude_unset=True))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(item_id: int, db: AsyncSession = Depends(get_async_db)):
    await delete_item(delivery_order_crud, db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
