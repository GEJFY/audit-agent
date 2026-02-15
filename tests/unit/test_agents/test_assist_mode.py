"""Assist Mode テスト"""

import pytest

from src.agents.assist_mode import (
    AssistModeConfig,
    AssistModeManager,
    AutoExecuteDecision,
    ExecutionMode,
)


@pytest.mark.unit
class TestExecutionMode:
    """ExecutionMode テスト"""

    def test_mode_values(self) -> None:
        """モード値の確認"""
        assert ExecutionMode.AUDIT.value == "audit"
        assert ExecutionMode.ASSIST.value == "assist"
        assert ExecutionMode.AUTONOMOUS.value == "autonomous"


@pytest.mark.unit
class TestAssistModeConfig:
    """AssistModeConfig テスト"""

    def test_default_config(self) -> None:
        """デフォルト設定"""
        config = AssistModeConfig()
        assert config.mode == ExecutionMode.AUDIT
        assert config.auto_approve_threshold == 0.85
        assert config.max_auto_approve_amount == 10_000_000
        assert len(config.allowed_auto_agents) > 0
        assert config.require_audit_trail is True

    def test_custom_config(self) -> None:
        """カスタム設定"""
        config = AssistModeConfig(
            mode=ExecutionMode.ASSIST,
            auto_approve_threshold=0.9,
            max_auto_approve_amount=50_000_000,
            allowed_auto_agents=["agent_a"],
        )
        assert config.mode == ExecutionMode.ASSIST
        assert config.auto_approve_threshold == 0.9


@pytest.mark.unit
class TestAssistModeManager:
    """AssistModeManager テスト"""

    def test_get_config_default(self) -> None:
        """デフォルト設定取得"""
        manager = AssistModeManager()
        config = manager.get_config("tenant1")
        assert config.mode == ExecutionMode.AUDIT

    def test_set_mode(self) -> None:
        """モード設定"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        assert manager.get_config("tenant1").mode == ExecutionMode.ASSIST

    def test_set_threshold(self) -> None:
        """閾値設定"""
        manager = AssistModeManager()
        manager.set_threshold("tenant1", 0.9)
        assert manager.get_config("tenant1").auto_approve_threshold == 0.9

    def test_set_threshold_invalid(self) -> None:
        """無効な閾値"""
        manager = AssistModeManager()
        with pytest.raises(ValueError, match=r"0.0〜1.0"):
            manager.set_threshold("tenant1", 1.5)
        with pytest.raises(ValueError, match=r"0.0〜1.0"):
            manager.set_threshold("tenant1", -0.1)

    def test_audit_mode_always_requires_approval(self) -> None:
        """Auditモードは常に人間承認必須"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.AUDIT)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.99,
        )
        assert decision.approved is False
        assert "Auditモード" in decision.reason
        assert decision.mode == ExecutionMode.AUDIT

    def test_autonomous_mode_always_auto(self) -> None:
        """Autonomousモードは常に自動実行"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.AUTONOMOUS)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="any_agent",
            confidence=0.1,
        )
        assert decision.approved is True
        assert decision.mode == ExecutionMode.AUTONOMOUS

    def test_assist_mode_high_confidence(self) -> None:
        """Assistモード — 高信頼度で自動実行"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.90,
        )
        assert decision.approved is True
        assert decision.confidence == 0.90

    def test_assist_mode_low_confidence(self) -> None:
        """Assistモード — 低信頼度は承認必須"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.50,
        )
        assert decision.approved is False
        assert "信頼度" in decision.reason

    def test_assist_mode_disallowed_agent(self) -> None:
        """Assistモード — 許可リスト外のエージェント"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditor_orchestrator",
            confidence=0.99,
        )
        assert decision.approved is False
        assert "自動実行対象外" in decision.reason

    def test_assist_mode_amount_limit(self) -> None:
        """Assistモード — 金額上限超過"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.95,
            amount=50_000_000,
        )
        assert decision.approved is False
        assert "金額" in decision.reason

    def test_assist_mode_amount_within_limit(self) -> None:
        """Assistモード — 金額上限内"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.95,
            amount=5_000_000,
        )
        assert decision.approved is True

    def test_assist_mode_no_amount(self) -> None:
        """Assistモード — 金額なし（チェックスキップ）"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.90,
            amount=None,
        )
        assert decision.approved is True

    def test_multiple_tenants_independent(self) -> None:
        """複数テナントは独立"""
        manager = AssistModeManager()
        manager.set_mode("tenant_a", ExecutionMode.AUDIT)
        manager.set_mode("tenant_b", ExecutionMode.ASSIST)

        assert manager.get_config("tenant_a").mode == ExecutionMode.AUDIT
        assert manager.get_config("tenant_b").mode == ExecutionMode.ASSIST

    def test_custom_threshold_affects_decision(self) -> None:
        """カスタム閾値が判定に影響"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        manager.set_threshold("tenant1", 0.95)

        # 0.90は閾値未満
        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.90,
        )
        assert decision.approved is False


@pytest.mark.unit
class TestAutoExecuteDecision:
    """AutoExecuteDecision テスト"""

    def test_approved_decision(self) -> None:
        """承認決定"""
        decision = AutoExecuteDecision(
            approved=True,
            reason="テスト",
            mode=ExecutionMode.ASSIST,
            confidence=0.9,
        )
        assert decision.approved is True
        assert decision.confidence == 0.9

    def test_rejected_decision(self) -> None:
        """却下決定"""
        decision = AutoExecuteDecision(
            approved=False,
            reason="信頼度不足",
            mode=ExecutionMode.ASSIST,
        )
        assert decision.approved is False
        assert decision.confidence is None
