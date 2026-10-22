from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.controller.base import CRUDBase


async def list_items(crud: CRUDBase, db: AsyncSession, skip: int, limit: int):
    try:
        return await crud.get_multi(db, skip=skip, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database query failed.") from exc


async def get_item(crud: CRUDBase, db: AsyncSession, item_id: int):
    try:
        item = await crud.get(db, item_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database query failed.") from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return item


async def create_item(crud: CRUDBase, db: AsyncSession, payload: dict[str, Any]):
    try:
        return await crud.create(db, obj_in=payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Unique or foreign-key constraint failed.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database insert failed.") from exc


async def update_item(
    crud: CRUDBase, db: AsyncSession, item_id: int, payload: dict[str, Any]
):
    item = await get_item(crud, db, item_id)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields supplied for update.")
    if any(value is None for value in payload.values()):
        raise HTTPException(status_code=422, detail="Null values are not allowed in updates.")
    try:
        return await crud.update(db, db_obj=item, obj_in=payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Database constraint failed.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database update failed.") from exc


async def delete_item(crud: CRUDBase, db: AsyncSession, item_id: int) -> None:
    await get_item(crud, db, item_id)
    try:
        await crud.remove(db, id=item_id)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Resource is referenced by another record and cannot be deleted.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database delete failed.") from exc
