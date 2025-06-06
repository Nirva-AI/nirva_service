from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime

""" 数据库迁移
alembic revision --autogenerate -m "Add display_name to UserDB"
alembic upgrade head
"""


# 基类定义
class Base(DeclarativeBase):
    pass


class UUIDBase(Base):
    """包含UUID主键的基类"""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True, index=True, default=uuid4)


# 用户模型
class UserDB(UUIDBase):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )
    # 新增创建时间字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # 新增更新时间字段
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
