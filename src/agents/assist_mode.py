"""Assist Mode — エージェント自動実行モード管理"""

from __future__ import annotations

from enum import StrEnum

from loguru import logger
from pydantic import BaseModel


class ExecutionMode(StrEnum):
    """エージェント実行モード"""

    AUDIT = "audit"  # 全て人間承認必須
    ASSIST = "assist"  # 高信頼度タスクは自動実行、低信頼度は承認必須
    AUTONOMOUS = "autonomous"  # 全て自動実行（テスト/デモ用）


class AssistModeConfig(BaseModel):
    """Assistモード設定"""

    mode: ExecutionMode = ExecutionMode.AUDIT
    auto_approve_threshold: float = 0.85  # Assistモード時の自動承認閾値
    max_auto_approve_amount: float = 10_000_000  # 自動承認可能な最大金額
    allowed_auto_agents: list[str] = [
        "auditee_response",
        "auditee_evidence_search",
        "auditee_prep",
    ]
    require_audit_trail: bool = True  # 自動実行でも監査証跡必須


class AssistModeManager:
    """Assistモード判定・管理

    テナント単位でエージェント実行モードを管理し、
    信頼度に基づいて自動実行可否を判定する。
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

    def can_auto_execute(
        self,
        tenant_id: str,
        agent_name: str,
        confidence: float,
        amount: float | None = None,
    ) -> AutoExecuteDecision:
        """自動実行可否を判定

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
            )

        # Autonomousモード: 常に自動実行
        if config.mode == ExecutionMode.AUTONOMOUS:
            return AutoExecuteDecision(
                approved=True,
                reason="Autonomousモード: 自動実行",
                mode=config.mode,
            )

        # Assistモード: 信頼度ベースの判定
        # エージェントが許可リストにあるか
        if agent_name not in config.allowed_auto_agents:
            return AutoExecuteDecision(
                approved=False,
                reason=f"エージェント '{agent_name}' は自動実行対象外",
                mode=config.mode,
            )

        # 信頼度チェック
        if confidence < config.auto_approve_threshold:
            return AutoExecuteDecision(
                approved=False,
                reason=f"信頼度 {confidence:.2f} < 閾値 {config.auto_approve_threshold:.2f}",
                mode=config.mode,
            )

        # 金額チェック
        if amount is not None and amount > config.max_auto_approve_amount:
            return AutoExecuteDecision(
                approved=False,
                reason=f"金額 {amount:,.0f} > 上限 {config.max_auto_approve_amount:,.0f}",
                mode=config.mode,
            )

        return AutoExecuteDecision(
            approved=True,
            reason="Assistモード: 条件充足により自動実行",
            mode=config.mode,
            confidence=confidence,
        )


class AutoExecuteDecision(BaseModel):
    """自動実行判定結果"""

    approved: bool
    reason: str
    mode: ExecutionMode
    confidence: float | None = None
