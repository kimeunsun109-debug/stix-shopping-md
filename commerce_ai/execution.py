# -*- coding: utf-8 -*-
"""Execution layer v6 — interface-based marketplace executors (approve-then-run)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from commerce_ai.models import ExecutionPlan, ExecutionStep, RecommendationCard
from commerce_ai.stability.errors import report_error
from commerce_ai.stability.logging_setup import get_logger
from commerce_ai.stability.resilience import RateLimiter, RetryPolicy, safe_call

_log = get_logger("commerce_ai.execution")
_EXEC_LIMITER = RateLimiter(max_calls=20, period_sec=60.0)
_EXEC_RETRY = RetryPolicy(max_attempts=2, base_delay_sec=0.3)


class MarketplaceExecutor(ABC):
    """Platform-specific adapter. Never mutates without explicit approval."""

    marketplace: str = "generic"
    live_api: bool = False  # True only when real credentials/API wired

    @abstractmethod
    def preview(self, action: str, params: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def supported_actions(self) -> list[str]:
        return [
            "title_update",
            "price_update",
            "image_update",
            "detail_update",
            "faq_update",
            "ad_budget",
            "review_reply",
            "stock_check",
        ]

    def _guarded_execute(
        self, action: str, params: dict[str, Any], impl
    ) -> dict[str, Any]:
        result = safe_call(
            impl,
            action,
            params,
            component=f"execution.{self.marketplace}.{action}",
            timeout_sec=25.0,
            retry=_EXEC_RETRY,
            rate_limiter=_EXEC_LIMITER,
            default={
                "ok": False,
                "dry_run": not self.live_api,
                "marketplace": self.marketplace,
                "action": action,
                "error": "execution failed safely",
            },
        )
        return result or {
            "ok": False,
            "marketplace": self.marketplace,
            "action": action,
            "error": "null result",
        }


class NoOpExecutor(MarketplaceExecutor):
    """Safe default — records intent only."""

    def __init__(self, marketplace: str = "coupang") -> None:
        self.marketplace = marketplace
        self.live_api = False

    def preview(self, action: str, params: dict[str, Any]) -> str:
        return f"[DRY-RUN {self.marketplace}.{action}] {params}"

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        def _run(a, p):
            _log.info("NoOp execute %s.%s", self.marketplace, a)
            return {
                "ok": True,
                "dry_run": True,
                "marketplace": self.marketplace,
                "action": a,
                "params": p,
                "message": "NoOpExecutor — API 미연결. 승인 로그만 기록.",
            }

        return self._guarded_execute(action, params, _run)


class CoupangExecutor(MarketplaceExecutor):
    """Coupang Wing API adapter stub — live_api=False until credentials set."""

    marketplace = "coupang"
    live_api = False

    def preview(self, action: str, params: dict[str, Any]) -> str:
        return f"[Coupang.{action} preview] product={params.get('product_id')} {params}"

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        def _run(a, p):
            if not self.live_api:
                return {
                    "ok": True,
                    "dry_run": True,
                    "marketplace": self.marketplace,
                    "action": a,
                    "params": p,
                    "message": "CoupangExecutor stub — Wing API 연결 전 dry-run",
                }
            raise NotImplementedError("Coupang live API not configured")

        return self._guarded_execute(action, params, _run)


class SmartStoreExecutor(MarketplaceExecutor):
    marketplace = "smartstore"
    live_api = False

    def preview(self, action: str, params: dict[str, Any]) -> str:
        return f"[SmartStore.{action} preview] {params}"

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        def _run(a, p):
            return {
                "ok": True,
                "dry_run": True,
                "marketplace": self.marketplace,
                "action": a,
                "params": p,
                "message": "SmartStoreExecutor stub — Commerce API 연결 전 dry-run",
            }

        return self._guarded_execute(action, params, _run)


class GmarketExecutor(MarketplaceExecutor):
    marketplace = "gmarket"
    live_api = False

    def preview(self, action: str, params: dict[str, Any]) -> str:
        return f"[Gmarket.{action} preview] {params}"

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        def _run(a, p):
            return {
                "ok": True,
                "dry_run": True,
                "marketplace": self.marketplace,
                "action": a,
                "params": p,
                "message": "GmarketExecutor stub — ESM API 연결 전 dry-run",
            }

        return self._guarded_execute(action, params, _run)


class AuctionExecutor(NoOpExecutor):
    def __init__(self) -> None:
        super().__init__("auction")


class ElevenStExecutor(NoOpExecutor):
    def __init__(self) -> None:
        super().__init__("11st")


class AmazonExecutor(NoOpExecutor):
    def __init__(self) -> None:
        super().__init__("amazon")


@dataclass
class ExecutorRegistry:
    _map: dict[str, MarketplaceExecutor] | None = None

    def __post_init__(self) -> None:
        if self._map is None:
            self._map = {
                "coupang": CoupangExecutor(),
                "smartstore": SmartStoreExecutor(),
                "gmarket": GmarketExecutor(),
                "auction": AuctionExecutor(),
                "11st": ElevenStExecutor(),
                "amazon": AmazonExecutor(),
            }

    def get(self, marketplace: str) -> MarketplaceExecutor:
        assert self._map is not None
        return self._map.get(marketplace) or NoOpExecutor(marketplace)

    def register(self, marketplace: str, executor: MarketplaceExecutor) -> None:
        assert self._map is not None
        self._map[marketplace] = executor


_ACTION_ADAPTER = {
    "상품명 변경": "title_update",
    "상품명 수정": "title_update",
    "대표이미지 교체": "image_update",
    "대표이미지 변경": "image_update",
    "가격 변경": "price_update",
    "FAQ 추가": "faq_update",
    "상세페이지 개선": "detail_update",
    "상세 상단 카피 교체": "detail_update",
    "Golden Keyword 반영": "title_update",
    "순위 급락 복구": "title_update",
    "재고 확인": "stock_check",
    "리뷰 답변 / 불만 선대응": "review_reply",
    "광고 ON/증액 검토": "ad_budget",
    "광고 OFF/축소 검토": "ad_budget",
}


class ExecutionPlanner:
    def __init__(self, registry: ExecutorRegistry | None = None) -> None:
        self.registry = registry or ExecutorRegistry()

    def build_plan(
        self,
        *,
        product_id: str,
        marketplace: str,
        keyword: str,
        recommendations: list[RecommendationCard],
    ) -> ExecutionPlan:
        executor = self.registry.get(marketplace)
        steps: list[ExecutionStep] = []
        for rec in recommendations:
            adapter = _ACTION_ADAPTER.get(rec.action, f"{rec.category}_update")
            params = dict(rec.payload)
            params["recommendation_id"] = rec.id
            params["expected_effect"] = rec.expected_effect
            params["product_id"] = product_id
            preview = safe_call(
                executor.preview,
                adapter,
                params,
                component="execution.preview",
                default=f"[preview-failed] {adapter}",
            )
            steps.append(
                ExecutionStep(
                    step_id=str(uuid4())[:8],
                    action=rec.action,
                    marketplace=marketplace,
                    product_id=product_id,
                    status="pending_approval",
                    adapter=f"{marketplace}.{adapter}",
                    params=params,
                    dry_run_preview=str(preview),
                    recommendation_id=rec.id,
                )
            )
        return ExecutionPlan(
            plan_id=str(uuid4())[:10],
            product_id=product_id,
            marketplace=marketplace,
            keyword=keyword,
            steps=steps,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

    def approve_step(
        self, plan: ExecutionPlan, step_id: str, *, execute: bool = False
    ) -> ExecutionStep:
        for step in plan.steps:
            if step.step_id != step_id:
                continue
            step.status = "approved"
            if execute:
                market, _, action = step.adapter.partition(".")
                try:
                    result = self.registry.get(market or plan.marketplace).execute(
                        action or "noop", step.params
                    )
                    step.status = "executed" if result.get("ok") else "failed"
                    step.params["execution_result"] = result
                except Exception as e:
                    report_error("execution.approve_step", e, recoverable=True)
                    step.status = "failed"
                    step.params["execution_result"] = {
                        "ok": False,
                        "error": str(e),
                    }
            return step
        raise KeyError(f"step not found: {step_id}")
