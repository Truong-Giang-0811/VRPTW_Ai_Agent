"""Cấu hình SQLAlchemy cho cả API async mới và routing legacy sync.

Các CRUD API dùng AsyncSession/get_async_db. Module routes_optimize.py hiện
vẫn dùng Session/get_db; giữ pool sync trong giai đoạn chuyển đổi để không làm
hỏng luồng tối ưu hiện tại. Có thể loại bỏ pool sync sau khi chuyển module đó.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME")

if not DB_USER or not DB_NAME:
    raise RuntimeError("Thiếu DB_USER hoặc DB_NAME trong file .env")

_common_url = dict(
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset": "utf8mb4"},
)

# Async engine: dùng cho CRUD API.
async_database_url = URL.create(drivername="mysql+asyncmy", **_common_url)
async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# Sync engine: tạm giữ cho app/controller/core/routes_optimize.py đang dùng
# db.query(...) và chưa được chuyển sang AsyncSession.
database_url = URL.create(drivername="mysql+pymysql", **_common_url)
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency đồng bộ dành riêng cho các endpoint legacy còn lại."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Dependency async dành cho toàn bộ CRUD API."""
    async with AsyncSessionLocal() as db:
        yield db


async def dispose_engines() -> None:
    """Đóng connection pools khi ứng dụng dừng."""
    await async_engine.dispose()
    engine.dispose()
