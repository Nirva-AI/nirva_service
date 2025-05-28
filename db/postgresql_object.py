from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
import datetime
from typing import List, Optional
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

    # 消息类型 (例如: "human", "ai", "system" 等)
    type: Mapped[str] = mapped_column(String(50))

    # 消息内容 - 存储为JSON以适应BaseMessage的结构
    content: Mapped[str] = mapped_column(Text)

    # 附加数据 - 存储BaseMessage中的其他属性
    additional_kwargs: Mapped[dict] = mapped_column(JSON, default=dict)

    # 关联关系
    session: Mapped["UserSessionDB"] = relationship(back_populates="messages")

    # 消息排序索引
    order_index: Mapped[int] = mapped_column(Integer)
