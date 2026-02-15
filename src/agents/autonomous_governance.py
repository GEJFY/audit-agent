"""Autonomous Governance — 意思決定監査ログ・自動レビュー・閾値管理

Autonomousモードで自動実行されたエージェント判断の
事後監査・説明可能性・ガバナンスを提供。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from src.agents.assist_mode import (
    AGENT_RISK_TIERS,
    AutoExecuteDecision,
)


@dataclass
class GovernanceLogEntry:
    """ガバナンスログエントリ — 1判断1エントリ"""

    decision_id: str
    tenant_id: str
    agent_name: str
    execution_mode: str  # assist / autonomous
    risk_tier: str
    confidence: float
    approved: bool
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    input_summary: dict[str, Any] = field(default_factory=dict)
    output_summary: dict[str, Any] = field(default_factory=dict)
    review_status: str = "pending"  # pending, reviewed, flagged
    reviewer_notes: str = ""


@dataclass
class GovernanceStats:
    """ガバナンス統計"""

    total_decisions: int = 0
    auto_approved: int = 0
    human_approved: int = 0
    auto_rejected: int = 0
    flagged_for_review: int = 0
    average_confidence: float = 0.0
    decisions_by_tier: dict[str, int] = field(default_factory=dict)
    decisions_by_agent: dict[str, int] = field(default_factory=dict)

    @property
    def auto_approval_rate(self) -> float:
        """自動承認率"""
        if self.total_decisions == 0:
            return 0.0
        return self.auto_approved / self.total_decisions


class AutonomousGovernance:
    """Autonomous意思決定ガバナンスエンジン

    責務:
    - 全自動実行判断の監査ログ記録
    - 事後レビューキューの管理
    - 異常パターン検出（連続エラー、信頼度低下等）
    - テナント別統計・ダッシュボードデータ提供
    """

    def __init__(self) -> None:
        self._logs: list[GovernanceLogEntry] = []
        self._tenant_stats: dict[str, GovernanceStats] = defaultdict(GovernanceStats)
        self._consecutive_errors: dict[str, int] = defaultdict(int)
        self._max_consecutive_errors: int = 5  # 自動停止閾値

    def record_decision(
        self,
        decision_id: str,
        tenant_id: str,
        agent_name: str,
        decision: AutoExecuteDecision,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
    ) -> GovernanceLogEntry:
        """判断をガバナンスログに記録"""
        entry = GovernanceLogEntry(
            decision_id=decision_id,
            tenant_id=tenant_id,
            agent_name=agent_name,
            execution_mode=decision.mode.value,
            risk_tier=decision.risk_tier.value,
            confidence=decision.confidence or 0.0,
            approved=decision.approved,
            reason=decision.reason,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
        )

        self._logs.append(entry)
        self._update_stats(tenant_id, entry)

        logger.debug(
            "ガバナンスログ記録: decision={}, agent={}, approved={}",
            decision_id,
            agent_name,
            decision.approved,
        )

        return entry

    def record_error(
        self,
        tenant_id: str,
        agent_name: str,
        error: str,
    ) -> bool:
        """エラーを記録し、連続エラー閾値超過をチェック

        Returns:
            True = 自動停止推奨
        """
        key = f"{tenant_id}:{agent_name}"
        self._consecutive_errors[key] += 1
        count = self._consecutive_errors[key]

        if count >= self._max_consecutive_errors:
            logger.warning(
                "連続エラー閾値超過: tenant={}, agent={}, count={}",
                tenant_id,
                agent_name,
                count,
            )
            return True

        return False

    def clear_error_count(self, tenant_id: str, agent_name: str) -> None:
        """成功時にエラーカウントをリセット"""
        key = f"{tenant_id}:{agent_name}"
        self._consecutive_errors[key] = 0

    def get_stats(self, tenant_id: str) -> GovernanceStats:
        """テナント別統計を取得"""
        return self._tenant_stats[tenant_id]

    def get_logs(
        self,
        tenant_id: str,
        agent_name: str | None = None,
        limit: int = 100,
    ) -> list[GovernanceLogEntry]:
        """ガバナンスログを取得"""
        filtered = [e for e in self._logs if e.tenant_id == tenant_id]

        if agent_name:
            filtered = [e for e in filtered if e.agent_name == agent_name]

        return filtered[-limit:]

    def get_pending_reviews(self, tenant_id: str) -> list[GovernanceLogEntry]:
        """レビュー待ちエントリを取得"""
        return [e for e in self._logs if e.tenant_id == tenant_id and e.review_status == "pending"]

    def mark_reviewed(
        self,
        decision_id: str,
        reviewer_notes: str = "",
    ) -> bool:
        """エントリをレビュー済みにマーク"""
        for entry in self._logs:
            if entry.decision_id == decision_id:
                entry.review_status = "reviewed"
                entry.reviewer_notes = reviewer_notes
                return True
        return False

    def flag_for_review(
        self,
        decision_id: str,
        reason: str = "",
    ) -> bool:
        """エントリをフラグ（要注意）にマーク"""
        for entry in self._logs:
            if entry.decision_id == decision_id:
                entry.review_status = "flagged"
                entry.reviewer_notes = reason
                stats = self._tenant_stats[entry.tenant_id]
                stats.flagged_for_review += 1
                return True
        return False

    def check_anomalous_pattern(self, tenant_id: str) -> list[str]:
        """異常パターンを検出

        Returns:
            検出された異常パターンの説明リスト
        """
        anomalies: list[str] = []
        stats = self._tenant_stats[tenant_id]

        # 自動承認率が高すぎる
        if stats.total_decisions >= 10 and stats.auto_approval_rate > 0.95:
            anomalies.append(f"自動承認率が異常に高い: {stats.auto_approval_rate:.1%}")

        # 平均信頼度が低い
        if stats.total_decisions >= 10 and stats.average_confidence < 0.7:
            anomalies.append(f"平均信頼度が低い: {stats.average_confidence:.2f}")

        # HIGHティア判断が多い
        high_count = stats.decisions_by_tier.get("high", 0)
        if stats.total_decisions >= 10 and high_count / stats.total_decisions > 0.5:
            anomalies.append(f"HIGHティア判断の比率が高い: {high_count}/{stats.total_decisions}")

        return anomalies

    def get_agent_summary(self) -> list[dict[str, Any]]:
        """全エージェントのリスクティア・閾値サマリーを返す"""
        return [
            {
                "agent_name": name,
                "risk_tier": tier.value,
            }
            for name, tier in sorted(AGENT_RISK_TIERS.items())
        ]

    def _update_stats(self, tenant_id: str, entry: GovernanceLogEntry) -> None:
        """統計を更新"""
        stats = self._tenant_stats[tenant_id]
        stats.total_decisions += 1

        if entry.approved:
            if entry.execution_mode in ("assist", "autonomous"):
                stats.auto_approved += 1
            else:
                stats.human_approved += 1
        else:
            stats.auto_rejected += 1

        # 移動平均で信頼度を更新
        n = stats.total_decisions
        stats.average_confidence = (stats.average_confidence * (n - 1) + entry.confidence) / n

        # ティア別カウント
        tier = entry.risk_tier
        stats.decisions_by_tier[tier] = stats.decisions_by_tier.get(tier, 0) + 1

        # エージェント別カウント
        agent = entry.agent_name
        stats.decisions_by_agent[agent] = stats.decisions_by_agent.get(agent, 0) + 1
