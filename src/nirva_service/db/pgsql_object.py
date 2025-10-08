from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, JSON
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
    events: Mapped["EventDB"] = relationship(
        "EventDB", back_populates="user"
    )
    daily_reflections: Mapped["DailyReflectionDB"] = relationship(
        "DailyReflectionDB", back_populates="user"
    )
    mental_state_scores: Mapped[List["MentalStateScoreDB"]] = relationship(
        "MentalStateScoreDB", back_populates="user"
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


# Mental State Scores
class MentalStateScoreDB(Base):
    __tablename__ = "user_mental_state_scores"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # User association
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    
    # Timestamp for the score
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    
    # Mental state scores
    energy_score: Mapped[float] = mapped_column(nullable=False)
    stress_score: Mapped[float] = mapped_column(nullable=False)
    
    # Confidence and source
    confidence: Mapped[float] = mapped_column(default=0.5, nullable=False)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'event', 'interpolated', 'baseline'
    event_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Reference if from event
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (
        {"extend_existing": True},
    )
    
    # Relationship
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="mental_state_scores")


# Event storage (replacing journal_files)
class EventDB(UUIDBase):
    __tablename__ = "events"
    
    # User association
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Event identification
    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    event_status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    
    # Event content
    event_title: Mapped[str] = mapped_column(String(500), nullable=False)
    event_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_story: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps (indexed for efficient querying)
    start_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    end_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Display fields
    time_range: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Metrics
    mood_score: Mapped[int] = mapped_column(nullable=False)
    stress_level: Mapped[int] = mapped_column(nullable=False)
    energy_level: Mapped[int] = mapped_column(nullable=False)
    
    # Categories
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    interaction_dynamic: Mapped[str] = mapped_column(String(50), nullable=False)
    inferred_impact_on_user_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # JSON fields for arrays
    mood_labels: Mapped[list] = mapped_column(JSON, nullable=False)
    people_involved: Mapped[list] = mapped_column(JSON, nullable=False)
    topic_labels: Mapped[list] = mapped_column(JSON, nullable=False)
    
    # Text fields
    one_sentence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    first_person_narrative: Mapped[str] = mapped_column(Text, nullable=False)
    action_item: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationship
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="events")


# Daily reflections (AI-generated summaries)
class DailyReflectionDB(UUIDBase):
    __tablename__ = "daily_reflections"
    
    # User association
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Date for the reflection (user's local date as string)
    reflection_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Reflection content as JSON (stores the entire DailyReflection model)
    reflection_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationship
    user: Mapped["UserDB"] = relationship("UserDB", back_populates="daily_reflections")


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
    
    # VAD (Voice Activity Detection) results
    speech_segments: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of [start, end] timestamps
    num_speech_segments: Mapped[Optional[int]] = mapped_column(nullable=True)
    total_speech_duration: Mapped[Optional[float]] = mapped_column(nullable=True)
    speech_ratio: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )  # Ratio of speech to total duration
    
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
    captured_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Actual time when audio was recorded/captured
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # Time when audio was uploaded to S3
    vad_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    
    # Batch association
    batch_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("audio_batches.id"), nullable=True, index=True
    )
    
    # Relationships
    user: Mapped["UserDB"] = relationship("UserDB", backref="audio_files")
    batch: Mapped["AudioBatchDB"] = relationship("AudioBatchDB", backref="audio_files")


# Audio batch for accumulating segments
class AudioBatchDB(UUIDBase):
    __tablename__ = "audio_batches"
    
    # Session/user association
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Batch timing
    first_segment_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_segment_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    
    # Batch status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="accumulating"
    )  # accumulating, processing, completed
    
    # Segment tracking
    segment_count: Mapped[int] = mapped_column(default=0)
    total_speech_duration: Mapped[float] = mapped_column(default=0.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# Transcription results
class TranscriptionResultDB(UUIDBase):
    __tablename__ = "transcription_results"
    
    # Session/user association
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Batch reference
    batch_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("audio_batches.id"), nullable=True, index=True
    )
    
    # Time range of the transcription (actual audio time range)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    
    # Transcription data
    transcription_text: Mapped[str] = mapped_column(Text, nullable=False)
    transcription_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    transcription_service: Mapped[str] = mapped_column(
        String(20), nullable=False, default="deepgram"
    )
    
    # Language detection
    detected_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Sentiment analysis (JSON array of sentiment scores per segment)
    sentiment_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Topics detection (JSON array of detected topics with confidence scores)
    topics_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Intents recognition (JSON array of detected intents with confidence scores)
    intents_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Full Deepgram response for future processing (compressed JSON)
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    num_segments: Mapped[int] = mapped_column(default=0)
    
    # Analysis tracking
    analysis_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    batch: Mapped["AudioBatchDB"] = relationship("AudioBatchDB", backref="transcription_results")


"""
SELECT * FROM journal_files WHERE username = 'weilyupku@gmail.com';

SELECT jf.*
FROM journal_files jf
JOIN users u ON jf.user_id = u.id
WHERE u.username = 'weilyupku@gmail.com';
"""
