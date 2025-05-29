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


# 基类定义
class Base(DeclarativeBase):
    pass


# 用户模型
class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 关联到用户会话
    sessions: Mapped[List["UserSessionDB"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


# 用户会话模型
class UserSessionDB(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
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
class ChatMessageDB(Base):
    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("user_sessions.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    # 将整个消息存储为JSON
    message_data: Mapped[Dict[str, Any]] = mapped_column(JSON)

    # 保留消息类型作为单独字段用于筛选(可选,但推荐)
    type: Mapped[str] = mapped_column(String(50))

    # 关联关系
    session: Mapped["UserSessionDB"] = relationship(back_populates="messages")

    # 消息排序索引
    order_index: Mapped[int] = mapped_column(Integer)
