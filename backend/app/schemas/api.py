"""Contrats Pydantic — API + sortie structurée du narrateur LLM."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------
# Sortie structurée du narrateur LLM
# ---------------------------------------------------------------

Priority = Literal["P0", "P1", "P2"]
AssertionType = Literal[
    "rupture", "surstock", "dormant", "acceleration", "opportunite", "reappro", "info"
]


class EvidenceItem(BaseModel):
    label: str
    value: Any


class LLMAssertion(BaseModel):
    priority: Priority
    type: AssertionType
    title: str = Field(..., max_length=200)
    message: str
    product_ref: str = ""
    product_name: str = ""
    confidence: float = Field(0.5, ge=0, le=1)
    action: str = ""
    evidence: list[EvidenceItem] = []


class LLMNarration(BaseModel):
    summary: str
    assertions: list[LLMAssertion]


# ---------------------------------------------------------------
# API — réponses
# ---------------------------------------------------------------


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref: str
    name: str
    category: str | None = None
    brand: str | None = None
    unit_price: float = 0.0
    margin_rate: float = 0.0
    supplier: str | None = None
    lead_time_days: int = 15
    min_order_qty: int = 1


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_ref: str = ""
    product_name: str = ""
    signal_type: str
    priority: str
    status: str
    metrics: dict[str, Any] | None = None
    computed_at: datetime


class AssertionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_date: date
    priority: str
    type: str
    title: str
    message: str
    product_ref: str | None = None
    product_name: str | None = None
    confidence: float
    action: str
    evidence: list | None = None
    feedback: str = "none"
    created_at: datetime


class ForecastPoint(BaseModel):
    date: date
    low: float
    mid: float
    high: float


class ForecastOut(BaseModel):
    product_ref: str
    product_name: str
    horizon_days: int
    points: list[ForecastPoint]


class Kpis(BaseModel):
    nb_ruptures: int = 0
    nb_overstock: int = 0
    nb_dormant: int = 0
    nb_opportunities: int = 0
    nb_reappro: int = 0
    avg_coverage_days: float = 0.0
    nb_products: int = 0


class Freshness(BaseModel):
    data_date: date | None = None
    is_fresh: bool = True
    last_ingestion: datetime | None = None
    source: str | None = None
    message: str = ""


class DecisionOut(BaseModel):
    priority: str = "P2"
    action_type: str = "surveiller"  # commander|ecouler|traiter|pousser|securiser|surveiller
    product_ref: str = ""
    product_name: str = ""
    quantity: int | None = None
    message: str = ""
    role: str = ""


class PilotageOut(BaseModel):
    report_date: date
    summary: str
    kpis: Kpis
    freshness: Freshness
    assertions: list[AssertionOut]
    decisions: list[DecisionOut] = []
    agent_last_run: datetime | None = None


class FeedbackIn(BaseModel):
    feedback: Literal["accurate", "inaccurate"]
    note: str | None = None


class AccuracyOut(BaseModel):
    score_date: date
    scope: str
    product_ref: str | None = None
    mape: float | None = None
    bias: float | None = None
    sample_size: int


class AgentRunResult(BaseModel):
    status: str
    message: str
    data_source: str
    nb_products: int = 0
    nb_forecast: int = 0
    nb_signals: int = 0
    nb_assertions: int = 0
    llm_used: bool = False
    duration_seconds: float = 0.0


class AgentJobOut(BaseModel):
    job_id: str | None = None
    status: str = "queued"  # queued|started|finished|failed
    mode: str | None = None
    result: AgentRunResult | None = None
    error: str | None = None
