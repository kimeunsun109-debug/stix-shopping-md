# -*- coding: utf-8 -*-
"""STIX Commerce AI v6.0 — Production Ready OS models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from seo_engine.models import CollectionBundle, RecoveryResult


@dataclass
class CommerceMetrics:
    revenue: int | None = None
    profit: int | None = None
    cost: int | None = None
    margin_pct: float | None = None
    units_sold: int | None = None
    impressions: int | None = None
    ctr: float | None = None
    cvr: float | None = None
    roas: float | None = None
    ad_spend: int | None = None
    rank: int | None = None
    stock: int | None = None
    conversions: int | None = None


@dataclass
class RevenueForecast:
    current_revenue: int
    projected_revenue: int
    lift_pct: float
    current_profit: int | None
    projected_profit: int | None
    profit_lift_pct: float | None
    projected_ctr: float | None
    projected_cvr: float | None
    projected_impressions: int | None
    projected_roas: float | None
    assumptions: list[str] = field(default_factory=list)


@dataclass
class PriceRecommendation:
    current_price: int | None
    recommended_price: int | None
    competitor_avg: float | None
    competitor_min: int | None
    competitor_max: int | None
    margin_delta_pct: float | None
    expected_rank_delta: int | None
    expected_volume_lift_pct: float | None
    expected_cvr_lift_pct: float | None
    reasons: list[str] = field(default_factory=list)


@dataclass
class AlertItem:
    severity: str
    code: str
    emoji: str
    message: str
    product_id: str = ""
    action: str = ""


@dataclass
class PlannerTask:
    priority: int
    title: str
    category: str
    expected_effect: str
    effort_minutes: int
    impact_score: float
    details: str = ""
    confidence: float = 0.0
    risk: str = "medium"
    difficulty: str = "easy"
    must_do_today: bool = True


@dataclass
class AutoRec:
    """v4 compat card — prefer RecommendationCard."""

    action: str
    expected_effect: str
    metric: str
    lift_pct: float
    priority: int


@dataclass
class ABTestPair:
    """A/B variants for approve-then-measure (no auto mutate)."""

    metric: str  # CTR|CVR|revenue|ROAS
    variant_a: str
    variant_b: str
    label_a: str = "A"
    label_b: str = "B"
    winner: str = ""  # A|B|tie|pending

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationCard:
    """Recommendation with confidence, evidence, failure risk, optional A/B."""

    id: str
    action: str
    category: str
    reason: str
    expected_effect: str
    metric: str
    lift_pct: float
    revenue_lift_pct: float
    priority: int
    risk: str
    effort_minutes: int
    confidence: float  # 0~100
    uncertainty: str = ""
    evidence: str = ""
    failure_risk: str = ""
    expected_impact: dict[str, float] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    must_do_today: bool = True
    ab_test: ABTestPair | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class ExecutionStep:
    step_id: str
    action: str
    marketplace: str
    product_id: str
    status: str = "pending_approval"
    adapter: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    dry_run_preview: str = ""
    recommendation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPlan:
    plan_id: str
    product_id: str
    marketplace: str
    keyword: str
    steps: list[ExecutionStep] = field(default_factory=list)
    created_at: str = ""
    notes: str = "AI는 직접 수정하지 않습니다. 승인 후 adapter 실행."

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "product_id": self.product_id,
            "marketplace": self.marketplace,
            "keyword": self.keyword,
            "created_at": self.created_at,
            "notes": self.notes,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class VerificationSnapshot:
    day: int
    rank: int | None = None
    ctr: float | None = None
    cvr: float | None = None
    revenue: int | None = None
    profit: int | None = None
    roas: float | None = None
    impressions: int | None = None
    conversions: int | None = None


@dataclass
class VerificationResult:
    recommendation_id: str
    action: str
    product_id: str
    status: str
    baseline: dict[str, Any]
    checkpoints: dict[str, VerificationSnapshot] = field(default_factory=dict)
    accuracy_notes: list[str] = field(default_factory=list)
    failure_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "action": self.action,
            "product_id": self.product_id,
            "status": self.status,
            "baseline": self.baseline,
            "checkpoints": {k: asdict(v) for k, v in self.checkpoints.items()},
            "accuracy_notes": self.accuracy_notes,
            "failure_reason": self.failure_reason,
        }


@dataclass
class VerificationMetrics:
    """Aggregate verification KPIs for dashboard / learning."""

    success_rate: float | None = None
    fail_rate: float | None = None
    n_success: int = 0
    n_fail: int = 0
    n_pending: int = 0
    avg_ctr_delta_pct: float | None = None
    avg_cvr_delta_pct: float | None = None
    avg_roas_delta_pct: float | None = None
    avg_revenue_delta_pct: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeContext:
    """Commerce Memory knowledge-base context for matching."""

    category: str = ""
    marketplace: str = ""
    season: str = ""
    price_band: str = ""
    image_traits: list[str] = field(default_factory=list)
    review_traits: list[str] = field(default_factory=list)


@dataclass
class CommerceResult:
    seo: RecoveryResult
    metrics: CommerceMetrics
    revenue_score: int
    revenue_forecast: RevenueForecast
    price_rec: PriceRecommendation
    alerts: list[AlertItem] = field(default_factory=list)
    planner_tasks: list[PlannerTask] = field(default_factory=list)
    auto_recs: list[AutoRec] = field(default_factory=list)
    recommendations: list[RecommendationCard] = field(default_factory=list)
    execution_plan: ExecutionPlan | None = None
    verification_due: list[dict[str, Any]] = field(default_factory=list)
    verification_metrics: VerificationMetrics | None = None
    competitor_changes: list[str] = field(default_factory=list)
    thumbnail_tips: list[str] = field(default_factory=list)
    commerce_score: int = 0
    recommendation_success_rate: float | None = None
    recommendation_fail_rate: float | None = None
    recommendation_accuracy: float | None = None
    memory_path: str = ""
    learning_path: str = ""
    memory_notes: list[str] = field(default_factory=list)
    learning_notes: list[str] = field(default_factory=list)
    system_health_ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "6.0",
            "seo_score": self.seo.seo_score,
            "revenue_score": self.revenue_score,
            "commerce_score": self.commerce_score,
            "metrics": asdict(self.metrics),
            "forecast": asdict(self.revenue_forecast),
            "price": asdict(self.price_rec),
            "alerts": [asdict(a) for a in self.alerts],
            "planner": [asdict(t) for t in self.planner_tasks],
            "auto_recs": [asdict(r) for r in self.auto_recs],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "execution_plan": self.execution_plan.to_dict()
            if self.execution_plan
            else None,
            "verification_due": self.verification_due,
            "verification_metrics": self.verification_metrics.to_dict()
            if self.verification_metrics
            else None,
            "recommendation_success_rate": self.recommendation_success_rate,
            "recommendation_fail_rate": self.recommendation_fail_rate,
            "recommendation_accuracy": self.recommendation_accuracy,
            "system_health_ok": self.system_health_ok,
        }


@dataclass
class CommerceInput:
    revenue: int | None = None
    profit: int | None = None
    cost: int | None = None
    units_sold: int | None = None
    impressions: int | None = None
    ctr: float | None = None
    cvr: float | None = None
    roas: float | None = None
    ad_spend: int | None = None
    stock: int | None = None
    rank: int | None = None
    rank_yesterday: int | None = None
    ctr_yesterday: float | None = None
    cvr_yesterday: float | None = None
    conversions: int | None = None
