# -*- coding: utf-8 -*-
"""Dependency injection container for Commerce AI v6."""
from __future__ import annotations

from dataclasses import dataclass, field

from commerce_ai.alerts import AlertCenter
from commerce_ai.confidence import ConfidenceEngine
from commerce_ai.execution import ExecutionPlanner, ExecutorRegistry
from commerce_ai.intelligence.competitor import CompetitorIntelligence
from commerce_ai.intelligence.price import PriceIntelligence
from commerce_ai.intelligence.revenue import RevenueIntelligence
from commerce_ai.intelligence.thumbnail import ThumbnailIntelligence
from commerce_ai.learning import CommerceLearningEngine
from commerce_ai.memory import CommerceMemory
from commerce_ai.monitoring import SystemMonitor
from commerce_ai.planner import AiMdPlanner
from commerce_ai.recommendation_engine import RecommendationEngine
from commerce_ai.verification import VerificationEngine
from seo_engine.analyzer import RecoveryAnalyzer


@dataclass
class CommerceContainer:
    """Composition root — inject mocks in tests."""

    seo: RecoveryAnalyzer = field(default_factory=RecoveryAnalyzer)
    revenue: RevenueIntelligence = field(default_factory=RevenueIntelligence)
    price: PriceIntelligence = field(default_factory=PriceIntelligence)
    competitor: CompetitorIntelligence = field(default_factory=CompetitorIntelligence)
    thumbnail: ThumbnailIntelligence = field(default_factory=ThumbnailIntelligence)
    alerts: AlertCenter = field(default_factory=AlertCenter)
    memory: CommerceMemory = field(default_factory=CommerceMemory)
    confidence: ConfidenceEngine | None = None
    recommendations: RecommendationEngine | None = None
    planner: AiMdPlanner = field(default_factory=AiMdPlanner)
    executors: ExecutorRegistry = field(default_factory=ExecutorRegistry)
    execution: ExecutionPlanner | None = None
    verification: VerificationEngine | None = None
    learning: CommerceLearningEngine = field(default_factory=CommerceLearningEngine)
    monitor: SystemMonitor = field(default_factory=SystemMonitor)

    def __post_init__(self) -> None:
        if self.confidence is None:
            self.confidence = ConfidenceEngine(self.memory)
        if self.recommendations is None:
            self.recommendations = RecommendationEngine(self.confidence)
        if self.execution is None:
            self.execution = ExecutionPlanner(self.executors)
        if self.verification is None:
            self.verification = VerificationEngine(memory=self.memory)


_default: CommerceContainer | None = None


def get_container() -> CommerceContainer:
    global _default
    if _default is None:
        _default = CommerceContainer()
    return _default


def set_container(container: CommerceContainer) -> None:
    global _default
    _default = container
