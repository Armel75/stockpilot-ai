"""Modèles SQLAlchemy — schéma de stockage de l'agent."""
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    margin_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0.30 = 30 %
    supplier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=15)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("product_id", "date", name="uq_sale_product_date"),
        Index("ix_sale_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"
    __table_args__ = (
        UniqueConstraint("product_id", "date", name="uq_stock_product_date"),
        Index("ix_stock_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    reserved: Mapped[float] = mapped_column(Float, default=0.0)
    in_transit: Mapped[float] = mapped_column(Float, default=0.0)


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (Index("ix_forecast_product_created", "product_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    forecast_date: Mapped[date] = mapped_column(Date)  # horizon (jour prévu)
    low: Mapped[float] = mapped_column(Float, default=0.0)
    mid: Mapped[float] = mapped_column(Float, default=0.0)
    high: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str] = mapped_column(String(30), default="ets")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (Index("ix_signal_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(30), index=True)
    # rupture|surstock|dormant|acceleration|opportunite|reappro
    priority: Mapped[str] = mapped_column(String(2))  # P0 | P1 | P2
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|resolved|dismissed
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Assertion(Base):
    __tablename__ = "assertions"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(2), index=True)  # P0 | P1 | P2
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    product_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    action: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{label, value}]
    feedback: Mapped[str] = mapped_column(String(20), default="none")  # none|accurate|inaccurate
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    nb_assertions: Mapped[int] = mapped_column(Integer, default=0)
    top_p0: Mapped[list | None] = mapped_column(JSON, nullable=True)
    kpis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccuracyScore(Base):
    __tablename__ = "accuracy_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    score_date: Mapped[date] = mapped_column(Date, index=True)
    scope: Mapped[str] = mapped_column(String(20))  # global | product
    product_ref: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)  # erreur moyenne %
    bias: Mapped[float | None] = mapped_column(Float, nullable=True)  # >0 = sur-prévision
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))  # sagex3 | seed
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # running|success|error
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")


class AgentRun(Base):
    """Trace d'une exécution de l'agent (file asynchrone RQ)."""
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(20), default="auto")
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|started|finished|failed
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
