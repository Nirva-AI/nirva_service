from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
import datetime
from typing import List, Optional, Dict, Any
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

    # 关联到用户会话
    sessions: Mapped[List["UserSessionDB"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# 用户会话模型
class UserSessionDB(UUIDBase):
    __tablename__ = "user_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))  # 从int改为UUID
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now
    )
    session_name: Mapped[Optional[str]] = mapped_column(String(255))

    # 关联关系
    user: Mapped["UserDB"] = relationship(back_populates="sessions")
    messages: Mapped[List["ChatMessageDB"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",  # 使用动态加载以支持分页
    )


# 聊天消息模型
class ChatMessageDB(UUIDBase):
    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(ForeignKey("user_sessions.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )

    # 将整个消息存储为JSON
    message_data: Mapped[Dict[str, Any]] = mapped_column(JSON)

    # 保留消息类型作为单独字段用于筛选(可选,但推荐)
    type: Mapped[str] = mapped_column(String(50))

    # 关联关系
    session: Mapped["UserSessionDB"] = relationship(back_populates="messages")

    # 消息排序索引
    order_index: Mapped[int] = mapped_column(Integer)
