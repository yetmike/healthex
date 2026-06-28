"""SQLAlchemy 2.0 ORM models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SleepSession(Base):
    __tablename__ = "sleep_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    civil_date: Mapped[date | None]
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sleep_type: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None]
    minutes_asleep: Mapped[int | None]
    minutes_awake: Mapped[int | None]
    minutes_light: Mapped[int | None]
    minutes_deep: Mapped[int | None]
    minutes_rem: Mapped[int | None]
    efficiency: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    sleep_score: Mapped[int | None]  # nullable/derived; may not be in API response
    source_platform: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("user_id", "start_time", name="uq_sleep_user_start"),
        Index("idx_sleep_user_date", "user_id", "civil_date"),
    )


class DailySteps(Base):
    __tablename__ = "daily_steps"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    step_date: Mapped[date] = mapped_column(nullable=False)
    steps: Mapped[int] = mapped_column(nullable=False)
    source_platform: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("user_id", "step_date", name="uq_steps_user_date"),
        Index("idx_steps_user_date", "user_id", "step_date"),
    )


class DailyRhr(Base):
    __tablename__ = "daily_rhr"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    rhr_date: Mapped[date] = mapped_column(nullable=False)
    bpm: Mapped[int] = mapped_column(nullable=False)
    calculation_method: Mapped[str | None] = mapped_column(Text)
    source_platform: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("user_id", "rhr_date", name="uq_rhr_user_date"),
        Index("idx_rhr_user_date", "user_id", "rhr_date"),
    )


class DailyHrv(Base):
    __tablename__ = "daily_hrv"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    hrv_date: Mapped[date] = mapped_column(nullable=False)
    avg_hrv_ms: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    non_rem_bpm: Mapped[int | None]
    entropy: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    deep_sleep_rmssd_ms: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    source_platform: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        UniqueConstraint("user_id", "hrv_date", name="uq_hrv_user_date"),
        Index("idx_hrv_user_date", "user_id", "hrv_date"),
    )
