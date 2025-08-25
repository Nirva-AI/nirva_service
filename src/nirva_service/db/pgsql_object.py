from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

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

    # 关系
    journal_files: Mapped["JournalFileDB"] = relationship(
        "JournalFileDB", back_populates="user"
    )


# 用户的日记数据
class JournalFileDB(UUIDBase):
    __tablename__ = "journal_files"

    # 关联到用户表
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 日期时间戳，用于识别特定日期的日记
    time_stamp: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 存储JournalFile的JSON序列化数据
    content_json: Mapped[str] = mapped_column(Text, nullable=False)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 关系
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="journal_files")


# Audio file tracking
class AudioFileDB(UUIDBase):
    __tablename__ = "audio_files"
    
    # User association
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True  # Nullable for native-audio uploads
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Stores session ID/hash
    
    # S3 location
    s3_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # File metadata
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded"
    )  # uploaded, processing, transcribed, failed
    
    # Transcription result
    transcription_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcription_service: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # aws, deepgram, etc
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", backref="audio_files")


"""
SELECT * FROM journal_files WHERE username = 'weilyupku@gmail.com';

SELECT jf.*
FROM journal_files jf
JOIN users u ON jf.user_id = u.id
WHERE u.username = 'weilyupku@gmail.com';
"""
