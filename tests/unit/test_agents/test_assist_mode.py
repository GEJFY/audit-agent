"""Assist Mode テスト — Phase 3: 全14エージェント + ティア別閾値"""

import pytest

from src.agents.assist_mode import (
    AGENT_RISK_TIERS,
    RISK_TIER_THRESHOLDS,
    AssistModeConfig,
    AssistModeManager,
    AutoExecuteDecision,
    ExecutionMode,
    RiskTier,
)


@pytest.mark.unit
class TestExecutionMode:
    """ExecutionMode テスト"""

    def test_mode_values(self) -> None:
        assert ExecutionMode.AUDIT.value == "audit"
        assert ExecutionMode.ASSIST.value == "assist"
        assert ExecutionMode.AUTONOMOUS.value == "autonomous"


@pytest.mark.unit
class TestRiskTier:
    """RiskTier テスト"""

    def test_tier_values(self) -> None:
        assert RiskTier.LOW.value == "low"
        assert RiskTier.MEDIUM.value == "medium"
        assert RiskTier.HIGH.value == "high"
        assert RiskTier.CRITICAL.value == "critical"

    def test_all_14_agents_mapped(self) -> None:
        """全14エージェントがマッピングされていること"""
        assert len(AGENT_RISK_TIERS) == 14

    def test_auditor_agents_mapped(self) -> None:
        auditor_agents = [k for k in AGENT_RISK_TIERS if k.startswith("auditor_")]
        assert len(auditor_agents) == 8

    def test_auditee_agents_mapped(self) -> None:
        auditee_agents = [k for k in AGENT_RISK_TIERS if k.startswith("auditee_")]
        assert len(auditee_agents) == 6

    def test_tier_thresholds_ascending(self) -> None:
        """ティア閾値が低→高の順"""
        assert RISK_TIER_THRESHOLDS[RiskTier.LOW] < RISK_TIER_THRESHOLDS[RiskTier.MEDIUM]
        assert RISK_TIER_THRESHOLDS[RiskTier.MEDIUM] < RISK_TIER_THRESHOLDS[RiskTier.HIGH]
        assert RISK_TIER_THRESHOLDS[RiskTier.HIGH] < RISK_TIER_THRESHOLDS[RiskTier.CRITICAL]


@pytest.mark.unit
class TestAssistModeConfig:
    """AssistModeConfig テスト"""

    def test_default_config(self) -> None:
        config = AssistModeConfig()
        assert config.mode == ExecutionMode.AUDIT
        assert config.auto_approve_threshold == 0.85
        assert config.max_auto_approve_amount == 10_000_000
        assert len(config.allowed_auto_agents) == 14
        assert config.require_audit_trail is True
        assert config.use_tiered_thresholds is True

    def test_custom_config(self) -> None:
        config = AssistModeConfig(
            mode=ExecutionMode.ASSIST,
            auto_approve_threshold=0.9,
            max_auto_approve_amount=50_000_000,
            allowed_auto_agents=["agent_a"],
        )
        assert config.mode == ExecutionMode.ASSIST
        assert config.auto_approve_threshold == 0.9

    def test_tiered_thresholds_disabled(self) -> None:
        config = AssistModeConfig(use_tiered_thresholds=False)
        assert config.use_tiered_thresholds is False


@pytest.mark.unit
class TestAssistModeManager:
    """AssistModeManager テスト"""

    def test_get_config_default(self) -> None:
        manager = AssistModeManager()
        config = manager.get_config("tenant1")
        assert config.mode == ExecutionMode.AUDIT

    def test_set_mode(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        assert manager.get_config("tenant1").mode == ExecutionMode.ASSIST

    def test_set_threshold(self) -> None:
        manager = AssistModeManager()
        manager.set_threshold("tenant1", 0.9)
        assert manager.get_config("tenant1").auto_approve_threshold == 0.9

    def test_set_threshold_invalid(self) -> None:
        manager = AssistModeManager()
        with pytest.raises(ValueError, match=r"0.0〜1.0"):
            manager.set_threshold("tenant1", 1.5)
        with pytest.raises(ValueError, match=r"0.0〜1.0"):
            manager.set_threshold("tenant1", -0.1)

    def test_audit_mode_always_requires_approval(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.AUDIT)
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_response", confidence=0.99)
        assert decision.approved is False
        assert "Auditモード" in decision.reason
        assert decision.mode == ExecutionMode.AUDIT

    def test_autonomous_mode_auto_execute(self) -> None:
        """Autonomousモード — 通常エージェントは自動実行"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.AUTONOMOUS)
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_response", confidence=0.5)
        assert decision.approved is True
        assert decision.mode == ExecutionMode.AUTONOMOUS

    def test_autonomous_mode_critical_tier_blocked(self) -> None:
        """Autonomousモード — CRITICALティアは人間承認"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.AUTONOMOUS)

        # CRITICALティアのエージェントを一時的に設定
        from src.agents import assist_mode

        original = assist_mode.AGENT_RISK_TIERS.get("auditor_orchestrator")
        assist_mode.AGENT_RISK_TIERS["auditor_orchestrator"] = RiskTier.CRITICAL
        try:
            decision = manager.can_auto_execute(
                tenant_id="tenant1",
                agent_name="auditor_orchestrator",
                confidence=0.99,
            )
            assert decision.approved is False
            assert "CRITICAL" in decision.reason
        finally:
            if original:
                assist_mode.AGENT_RISK_TIERS["auditor_orchestrator"] = original

    def test_autonomous_mode_high_risk_level_blocked(self) -> None:
        """Autonomousモード — リスクレベル high/critical は人間承認"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.AUTONOMOUS)

        decision_high = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.99,
            risk_level="high",
        )
        assert decision_high.approved is False
        assert "リスクレベル" in decision_high.reason

        decision_critical = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_response",
            confidence=0.99,
            risk_level="critical",
        )
        assert decision_critical.approved is False

    def test_assist_mode_high_confidence(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_response", confidence=0.90)
        assert decision.approved is True
        assert decision.confidence == 0.90

    def test_assist_mode_low_confidence(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_response", confidence=0.50)
        assert decision.approved is False
        assert "信頼度" in decision.reason

    def test_assist_mode_disallowed_agent(self) -> None:
        """許可リストを制限した場合"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        config = manager.get_config("tenant1")
        config.allowed_auto_agents = ["auditee_response"]

        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditor_orchestrator", confidence=0.99)
        assert decision.approved is False
        assert "自動実行対象外" in decision.reason

    def test_assist_mode_amount_limit(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_evidence_search",
            confidence=0.95,
            amount=50_000_000,
        )
        assert decision.approved is False
        assert "金額" in decision.reason

    def test_assist_mode_amount_within_limit(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_evidence_search",
            confidence=0.95,
            amount=5_000_000,
        )
        assert decision.approved is True

    def test_assist_mode_no_amount(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_evidence_search",
            confidence=0.90,
            amount=None,
        )
        assert decision.approved is True

    def test_multiple_tenants_independent(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant_a", ExecutionMode.AUDIT)
        manager.set_mode("tenant_b", ExecutionMode.ASSIST)
        assert manager.get_config("tenant_a").mode == ExecutionMode.AUDIT
        assert manager.get_config("tenant_b").mode == ExecutionMode.ASSIST

    def test_custom_threshold_affects_decision(self) -> None:
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        manager.set_threshold("tenant1", 0.95)
        # ティア閾値を無効化してグローバル閾値を使用
        config = manager.get_config("tenant1")
        config.use_tiered_thresholds = False

        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_response", confidence=0.90)
        assert decision.approved is False

    def test_tiered_threshold_low_tier(self) -> None:
        """LOWティアエージェントは0.70で通過"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_evidence_search", confidence=0.75)
        assert decision.approved is True

    def test_tiered_threshold_high_tier(self) -> None:
        """HIGHティアエージェントは0.92が必要"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)

        # 0.90 < 0.92 → 却下
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditor_planner", confidence=0.90)
        assert decision.approved is False

        # 0.95 >= 0.92 → 承認
        decision2 = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditor_planner", confidence=0.95)
        assert decision2.approved is True

    def test_get_effective_threshold(self) -> None:
        manager = AssistModeManager()
        # LOWティア
        t1 = manager.get_effective_threshold("t", "auditee_evidence_search")
        assert t1 == 0.70
        # HIGHティア
        t2 = manager.get_effective_threshold("t", "auditor_planner")
        assert t2 == 0.92

    def test_get_effective_threshold_global_fallback(self) -> None:
        """ティア無効時はグローバル閾値"""
        manager = AssistModeManager()
        config = manager.get_config("t")
        config.use_tiered_thresholds = False
        config.auto_approve_threshold = 0.80

        threshold = manager.get_effective_threshold("t", "auditee_response")
        assert threshold == 0.80

    def test_get_effective_threshold_custom_override(self) -> None:
        """カスタム上書き"""
        manager = AssistModeManager()
        config = manager.get_config("t")
        config.custom_tier_thresholds = {"auditee_response": 0.60}

        threshold = manager.get_effective_threshold("t", "auditee_response")
        assert threshold == 0.60

    def test_get_agent_risk_tier(self) -> None:
        manager = AssistModeManager()
        assert manager.get_agent_risk_tier("auditee_evidence_search") == RiskTier.LOW
        assert manager.get_agent_risk_tier("auditee_response") == RiskTier.MEDIUM
        assert manager.get_agent_risk_tier("auditor_planner") == RiskTier.HIGH
        # 未知のエージェント → HIGH
        assert manager.get_agent_risk_tier("unknown_agent") == RiskTier.HIGH

    def test_assist_mode_critical_risk_level_blocked(self) -> None:
        """Assistモード — リスクレベルcriticalは自動実行不可"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(
            tenant_id="tenant1",
            agent_name="auditee_evidence_search",
            confidence=0.99,
            risk_level="critical",
        )
        assert decision.approved is False
        assert "リスクレベル" in decision.reason

    def test_risk_tier_in_decision(self) -> None:
        """判定結果にリスクティアが含まれる"""
        manager = AssistModeManager()
        manager.set_mode("tenant1", ExecutionMode.ASSIST)
        decision = manager.can_auto_execute(tenant_id="tenant1", agent_name="auditee_evidence_search", confidence=0.90)
        assert decision.risk_tier == RiskTier.LOW


@pytest.mark.unit
class TestAutoExecuteDecision:
    """AutoExecuteDecision テスト"""

    def test_approved_decision(self) -> None:
        decision = AutoExecuteDecision(
            approved=True,
            reason="テスト",
            mode=ExecutionMode.ASSIST,
            confidence=0.9,
            risk_tier=RiskTier.MEDIUM,
        )
        assert decision.approved is True
        assert decision.confidence == 0.9
        assert decision.risk_tier == RiskTier.MEDIUM

    def test_rejected_decision(self) -> None:
        decision = AutoExecuteDecision(
            approved=False,
            reason="信頼度不足",
            mode=ExecutionMode.ASSIST,
        )
        assert decision.approved is False
        assert decision.confidence is None
        assert decision.risk_tier == RiskTier.MEDIUM  # default
