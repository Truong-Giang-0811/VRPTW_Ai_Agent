from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connect_db import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """CRUD bất đồng bộ dùng chung cho các model SQLAlchemy."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> ModelType | None:
        return await db.get(self.model, id)

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        if skip < 0:
            raise ValueError("skip không được âm")
        if not 1 <= limit <= 500:
            raise ValueError("limit phải nằm trong khoảng 1-500")

        statement = select(self.model).offset(skip).limit(limit)
        result = await db.scalars(statement)
        return list(result.all())

    async def create(self, db: AsyncSession, *, obj_in: dict[str, Any]) -> ModelType:
        db_obj = self.model(**obj_in)
        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception:
            await db.rollback()
            raise

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        valid_fields = set(self.model.__table__.columns.keys())
        for field, value in obj_in.items():
            if field not in valid_fields or field == "id":
                raise ValueError(f"Trường không hợp lệ: {field}")
            setattr(db_obj, field, value)

        try:
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except Exception:
            await db.rollback()
            raise

    async def remove(self, db: AsyncSession, *, id: int) -> ModelType | None:
        db_obj = await self.get(db, id)
        if db_obj is None:
            return None
        try:
            await db.delete(db_obj)
            await db.commit()
            return db_obj
        except Exception:
            await db.rollback()
            raise
