"""Assist Mode — エージェント自動実行モード管理

Phase 3: 全14エージェント対応、段階的信頼度閾値、リスク連動ゲート
"""

from __future__ import annotations

from enum import StrEnum

from loguru import logger
from pydantic import BaseModel


class ExecutionMode(StrEnum):
    """エージェント実行モード"""

    AUDIT = "audit"  # 全て人間承認必須
    ASSIST = "assist"  # 高信頼度タスクは自動実行、低信頼度は承認必須
    AUTONOMOUS = "autonomous"  # 自律実行（ガバナンス制約付き）


class RiskTier(StrEnum):
    """エージェントリスクティア — 操作の影響度に基づく分類"""

    LOW = "low"  # 情報参照・検索のみ（承認不要の傾向）
    MEDIUM = "medium"  # データ分析・ドラフト生成（標準閾値）
    HIGH = "high"  # 判断・レポート・外部通知（高閾値）
    CRITICAL = "critical"  # エスカレーション・最終承認（常に人間承認）


# ── エージェント別リスクティアマッピング ──────────────────
AGENT_RISK_TIERS: dict[str, RiskTier] = {
    # 監査側 (8エージェント)
    "auditor_orchestrator": RiskTier.HIGH,
    "auditor_planner": RiskTier.HIGH,
    "auditor_data_collector": RiskTier.LOW,
    "auditor_controls_tester": RiskTier.MEDIUM,
    "auditor_anomaly_detective": RiskTier.MEDIUM,
    "auditor_report_writer": RiskTier.HIGH,
    "auditor_follow_up": RiskTier.MEDIUM,
    "auditor_knowledge": RiskTier.LOW,
    # 被監査側 (6エージェント)
    "auditee_orchestrator": RiskTier.MEDIUM,
    "auditee_response": RiskTier.MEDIUM,
    "auditee_evidence_search": RiskTier.LOW,
    "auditee_prep": RiskTier.LOW,
    "auditee_risk_alert": RiskTier.HIGH,
    "auditee_controls_monitor": RiskTier.LOW,
}

# ── リスクティア別デフォルト閾値 ─────────────────────────
RISK_TIER_THRESHOLDS: dict[RiskTier, float] = {
    RiskTier.LOW: 0.70,
    RiskTier.MEDIUM: 0.85,
    RiskTier.HIGH: 0.92,
    RiskTier.CRITICAL: 1.01,  # 実質常に人間承認
}


class AssistModeConfig(BaseModel):
    """Assistモード設定"""

    mode: ExecutionMode = ExecutionMode.AUDIT
    auto_approve_threshold: float = 0.85  # グローバル閾値（ティア別で上書き可）
    max_auto_approve_amount: float = 10_000_000
    allowed_auto_agents: list[str] = list(AGENT_RISK_TIERS.keys())
    require_audit_trail: bool = True
    use_tiered_thresholds: bool = True  # ティア別閾値を使用
    custom_tier_thresholds: dict[str, float] | None = None  # カスタム上書き


class AssistModeManager:
    """Assistモード判定・管理

    テナント単位でエージェント実行モードを管理し、
    リスクティアと信頼度に基づいて自動実行可否を判定する。
    """

    def __init__(self) -> None:
        self._tenant_configs: dict[str, AssistModeConfig] = {}

    def get_config(self, tenant_id: str) -> AssistModeConfig:
        """テナントのAssistモード設定を取得"""
        if tenant_id not in self._tenant_configs:
            self._tenant_configs[tenant_id] = AssistModeConfig()
        return self._tenant_configs[tenant_id]

    def set_mode(self, tenant_id: str, mode: ExecutionMode) -> None:
        """テナントの実行モードを設定"""
        config = self.get_config(tenant_id)
        config.mode = mode
        logger.info("実行モード変更: tenant={}, mode={}", tenant_id, mode.value)

    def set_threshold(self, tenant_id: str, threshold: float) -> None:
        """テナントの自動承認閾値を設定"""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("閾値は0.0〜1.0の範囲で指定してください")
        config = self.get_config(tenant_id)
        config.auto_approve_threshold = threshold

    def get_effective_threshold(self, tenant_id: str, agent_name: str) -> float:
        """エージェントの実効閾値を取得（ティア別 or グローバル）"""
        config = self.get_config(tenant_id)

        if not config.use_tiered_thresholds:
            return config.auto_approve_threshold

        # カスタム上書きを優先
        if config.custom_tier_thresholds and agent_name in config.custom_tier_thresholds:
            return config.custom_tier_thresholds[agent_name]

        tier = AGENT_RISK_TIERS.get(agent_name, RiskTier.HIGH)
        return RISK_TIER_THRESHOLDS[tier]

    def get_agent_risk_tier(self, agent_name: str) -> RiskTier:
        """エージェントのリスクティアを取得"""
        return AGENT_RISK_TIERS.get(agent_name, RiskTier.HIGH)

    def can_auto_execute(
        self,
        tenant_id: str,
        agent_name: str,
        confidence: float,
        amount: float | None = None,
        risk_level: str | None = None,
    ) -> AutoExecuteDecision:
        """自動実行可否を判定

        Args:
            tenant_id: テナントID
            agent_name: エージェント名
            confidence: 信頼度スコア (0-1)
            amount: 関連金額（任意）
            risk_level: 現在のリスクレベル（任意、"critical"/"high"等）

        Returns:
            AutoExecuteDecision（承認/却下の詳細情報）
        """
        config = self.get_config(tenant_id)

        # Auditモード: 常に人間承認必須
        if config.mode == ExecutionMode.AUDIT:
            return AutoExecuteDecision(
                approved=False,
                reason="Auditモード: 全て人間承認必須",
                mode=config.mode,
                risk_tier=self.get_agent_risk_tier(agent_name),
            )

        # Autonomousモード: ガバナンス付き自動実行
        if config.mode == ExecutionMode.AUTONOMOUS:
            # CRITICALティアはAutonomousでも人間承認
            tier = self.get_agent_risk_tier(agent_name)
            if tier == RiskTier.CRITICAL:
                return AutoExecuteDecision(
                    approved=False,
                    reason="CRITICALティア: Autonomousモードでも人間承認必須",
                    mode=config.mode,
                    risk_tier=tier,
                )
            # リスクレベルがcritical/highの場合はAutonomousでも承認必須
            if risk_level in ("critical", "high"):
                return AutoExecuteDecision(
                    approved=False,
                    reason=f"リスクレベル '{risk_level}': Autonomousモードでも人間承認必須",
                    mode=config.mode,
                    risk_tier=tier,
                )
            return AutoExecuteDecision(
                approved=True,
                reason="Autonomousモード: 自動実行",
                mode=config.mode,
                risk_tier=tier,
            )

        # Assistモード: 信頼度 + ティアベースの判定
        tier = self.get_agent_risk_tier(agent_name)

        # エージェントが許可リストにあるか
        if agent_name not in config.allowed_auto_agents:
            return AutoExecuteDecision(
                approved=False,
                reason=f"エージェント '{agent_name}' は自動実行対象外",
                mode=config.mode,
                risk_tier=tier,
            )

        # CRITICALティアは常に人間承認
        if tier == RiskTier.CRITICAL:
            return AutoExecuteDecision(
                approved=False,
                reason="CRITICALティア: 常に人間承認必須",
                mode=config.mode,
                risk_tier=tier,
            )

        # リスクレベルによるゲート
        if risk_level == "critical":
            return AutoExecuteDecision(
                approved=False,
                reason="リスクレベル 'critical': 自動実行不可",
                mode=config.mode,
                risk_tier=tier,
            )

        # 実効閾値を取得（ティア別）
        effective_threshold = self.get_effective_threshold(tenant_id, agent_name)

        # 信頼度チェック
        if confidence < effective_threshold:
            return AutoExecuteDecision(
                approved=False,
                reason=(f"信頼度 {confidence:.2f} < 閾値 {effective_threshold:.2f} (ティア: {tier.value})"),
                mode=config.mode,
                risk_tier=tier,
            )

        # 金額チェック
        if amount is not None and amount > config.max_auto_approve_amount:
            return AutoExecuteDecision(
                approved=False,
                reason=f"金額 {amount:,.0f} > 上限 {config.max_auto_approve_amount:,.0f}",
                mode=config.mode,
                risk_tier=tier,
            )

        return AutoExecuteDecision(
            approved=True,
            reason="Assistモード: 条件充足により自動実行",
            mode=config.mode,
            confidence=confidence,
            risk_tier=tier,
        )


class AutoExecuteDecision(BaseModel):
    """自動実行判定結果"""

    approved: bool
    reason: str
    mode: ExecutionMode
    confidence: float | None = None
    risk_tier: RiskTier = RiskTier.MEDIUM
