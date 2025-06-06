from sqlalchemy import String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from typing import Optional
from uuid import uuid4, UUID

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
