"""SLA監視 — テナントTier別のSLA目標管理・違反検出"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger


class SLAMetricType(StrEnum):
    """SLAメトリクス種別"""

    API_RESPONSE_TIME = "api_response_time"
    LLM_LATENCY = "llm_latency"
    UPTIME = "uptime"
    AUDIT_COMPLETION = "audit_completion"
    EVIDENCE_PROCESSING = "evidence_processing"


@dataclass
class SLATarget:
    """SLA目標値"""

    metric: SLAMetricType
    threshold_ms: float  # レスポンスタイム系: ミリ秒
    threshold_percent: float = 99.9  # 可用性系: パーセント
    evaluation_window_hours: int = 24


@dataclass
class SLARecord:
    """SLAメトリクス記録"""

    metric: SLAMetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    tenant_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SLAViolation:
    """SLA違反"""

    metric: SLAMetricType
    target_value: float
    actual_value: float
    tenant_id: str
    severity: str  # warning, critical
    message: str


class SLAMonitor:
    """SLA監視サービス

    テナントTier別のSLA目標を管理し、メトリクスを記録・評価する。
    閾値超過時にSLA違反を検出してアラートを発行。
    """

    # Tier別SLA目標（デフォルト）
    TIER_TARGETS: dict[str, list[SLATarget]] = {
        "enterprise": [
            SLATarget(metric=SLAMetricType.API_RESPONSE_TIME, threshold_ms=500),
            SLATarget(metric=SLAMetricType.LLM_LATENCY, threshold_ms=5000),
            SLATarget(metric=SLAMetricType.UPTIME, threshold_ms=0, threshold_percent=99.9),
        ],
        "professional": [
            SLATarget(metric=SLAMetricType.API_RESPONSE_TIME, threshold_ms=1000),
            SLATarget(metric=SLAMetricType.LLM_LATENCY, threshold_ms=10000),
            SLATarget(metric=SLAMetricType.UPTIME, threshold_ms=0, threshold_percent=99.5),
        ],
        "starter": [
            SLATarget(metric=SLAMetricType.API_RESPONSE_TIME, threshold_ms=2000),
            SLATarget(metric=SLAMetricType.LLM_LATENCY, threshold_ms=15000),
            SLATarget(metric=SLAMetricType.UPTIME, threshold_ms=0, threshold_percent=99.0),
        ],
    }

    def __init__(self) -> None:
        self._records: dict[str, list[SLARecord]] = defaultdict(list)
        self._violations: list[SLAViolation] = []

    def record_metric(self, record: SLARecord) -> None:
        """メトリクスを記録"""
        key = f"{record.tenant_id}:{record.metric}"
        self._records[key].append(record)

    def get_targets(self, tier: str) -> list[SLATarget]:
        """Tier別SLA目標を取得"""
        return self.TIER_TARGETS.get(tier, self.TIER_TARGETS["starter"])

    def evaluate(self, tenant_id: str, tier: str = "starter") -> list[SLAViolation]:
        """テナントのSLA違反を評価"""
        targets = self.get_targets(tier)
        violations: list[SLAViolation] = []

        for target in targets:
            key = f"{tenant_id}:{target.metric}"
            records = self._records.get(key, [])
            if not records:
                continue

            if target.metric == SLAMetricType.UPTIME:
                violation = self._evaluate_uptime(tenant_id, target, records)
            else:
                violation = self._evaluate_latency(tenant_id, target, records)

            if violation:
                violations.append(violation)
                self._violations.append(violation)

        if violations:
            logger.warning(
                "SLA違反検出: tenant={}, violations={}",
                tenant_id,
                len(violations),
            )

        return violations

    def _evaluate_latency(
        self,
        tenant_id: str,
        target: SLATarget,
        records: list[SLARecord],
    ) -> SLAViolation | None:
        """レイテンシ系メトリクスの評価"""
        values = [r.value for r in records]
        avg_value = sum(values) / len(values)

        if avg_value > target.threshold_ms:
            severity = "critical" if avg_value > target.threshold_ms * 2 else "warning"
            return SLAViolation(
                metric=target.metric,
                target_value=target.threshold_ms,
                actual_value=round(avg_value, 2),
                tenant_id=tenant_id,
                severity=severity,
                message=(f"{target.metric}: 平均 {avg_value:.0f}ms (目標: {target.threshold_ms:.0f}ms)"),
            )
        return None

    def _evaluate_uptime(
        self,
        tenant_id: str,
        target: SLATarget,
        records: list[SLARecord],
    ) -> SLAViolation | None:
        """可用性メトリクスの評価"""
        values = [r.value for r in records]
        avg_uptime = sum(values) / len(values)

        if avg_uptime < target.threshold_percent:
            severity = "critical" if avg_uptime < target.threshold_percent - 1 else "warning"
            return SLAViolation(
                metric=target.metric,
                target_value=target.threshold_percent,
                actual_value=round(avg_uptime, 2),
                tenant_id=tenant_id,
                severity=severity,
                message=(f"可用性: {avg_uptime:.2f}% (目標: {target.threshold_percent}%)"),
            )
        return None

    def get_violations(self, tenant_id: str | None = None) -> list[SLAViolation]:
        """SLA違反一覧を取得"""
        if tenant_id:
            return [v for v in self._violations if v.tenant_id == tenant_id]
        return list(self._violations)

    def get_summary(self, tenant_id: str) -> dict[str, Any]:
        """テナントのSLAサマリー"""
        total_records = 0
        metrics: dict[str, dict[str, Any]] = {}

        for key, records in self._records.items():
            if not key.startswith(f"{tenant_id}:"):
                continue
            metric_name = key.split(":", 1)[1]
            values = [r.value for r in records]
            total_records += len(values)
            metrics[metric_name] = {
                "count": len(values),
                "avg": round(sum(values) / len(values), 2) if values else 0,
                "min": round(min(values), 2) if values else 0,
                "max": round(max(values), 2) if values else 0,
            }

        violations = self.get_violations(tenant_id)
        return {
            "tenant_id": tenant_id,
            "total_records": total_records,
            "metrics": metrics,
            "violations_count": len(violations),
            "violations": [
                {
                    "metric": v.metric,
                    "severity": v.severity,
                    "message": v.message,
                }
                for v in violations
            ],
        }

    def reset(self) -> None:
        """モニターをリセット"""
        self._records.clear()
        self._violations.clear()
