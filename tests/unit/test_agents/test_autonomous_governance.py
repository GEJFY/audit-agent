"""Autonomous Governance テスト"""

import pytest

from src.agents.assist_mode import AutoExecuteDecision, ExecutionMode, RiskTier
from src.agents.autonomous_governance import (
    AutonomousGovernance,
    GovernanceLogEntry,
    GovernanceStats,
)


@pytest.mark.unit
class TestGovernanceLogEntry:
    """ログエントリのテスト"""

    def test_create_entry(self) -> None:
        entry = GovernanceLogEntry(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            execution_mode="assist",
            risk_tier="medium",
            confidence=0.9,
            approved=True,
            reason="条件充足",
        )
        assert entry.decision_id == "d-001"
        assert entry.review_status == "pending"
        assert entry.timestamp  # 自動設定

    def test_default_fields(self) -> None:
        entry = GovernanceLogEntry(
            decision_id="d-002",
            tenant_id="t-001",
            agent_name="auditee_prep",
            execution_mode="autonomous",
            risk_tier="low",
            confidence=0.8,
            approved=True,
            reason="Autonomousモード",
        )
        assert entry.input_summary == {}
        assert entry.output_summary == {}
        assert entry.reviewer_notes == ""


@pytest.mark.unit
class TestGovernanceStats:
    """統計データクラスのテスト"""

    def test_default_stats(self) -> None:
        stats = GovernanceStats()
        assert stats.total_decisions == 0
        assert stats.auto_approved == 0
        assert stats.auto_approval_rate == 0.0

    def test_auto_approval_rate(self) -> None:
        stats = GovernanceStats(
            total_decisions=10,
            auto_approved=7,
            human_approved=2,
            auto_rejected=1,
        )
        assert stats.auto_approval_rate == 0.7


@pytest.mark.unit
class TestAutonomousGovernance:
    """AutonomousGovernance テスト"""

    def _make_decision(self, approved: bool = True, confidence: float = 0.9) -> AutoExecuteDecision:
        return AutoExecuteDecision(
            approved=approved,
            reason="テスト",
            mode=ExecutionMode.ASSIST,
            confidence=confidence,
            risk_tier=RiskTier.MEDIUM,
        )

    def test_record_decision(self) -> None:
        gov = AutonomousGovernance()
        decision = self._make_decision()
        entry = gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=decision,
        )
        assert entry.decision_id == "d-001"
        assert entry.approved is True

    def test_record_updates_stats(self) -> None:
        gov = AutonomousGovernance()
        decision = self._make_decision()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=decision,
        )
        stats = gov.get_stats("t-001")
        assert stats.total_decisions == 1
        assert stats.auto_approved == 1
        assert stats.average_confidence == 0.9

    def test_multiple_decisions_stats(self) -> None:
        gov = AutonomousGovernance()
        for i in range(5):
            gov.record_decision(
                decision_id=f"d-{i:03d}",
                tenant_id="t-001",
                agent_name="auditee_response",
                decision=self._make_decision(confidence=0.8 + i * 0.02),
            )
        stats = gov.get_stats("t-001")
        assert stats.total_decisions == 5
        assert stats.auto_approved == 5

    def test_rejected_decision_stats(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(approved=False),
        )
        stats = gov.get_stats("t-001")
        assert stats.auto_rejected == 1

    def test_record_error(self) -> None:
        gov = AutonomousGovernance()
        for i in range(4):
            result = gov.record_error("t-001", "auditee_response", f"error-{i}")
            assert result is False  # まだ閾値未超過

        result = gov.record_error("t-001", "auditee_response", "error-4")
        assert result is True  # 5回目で閾値超過

    def test_clear_error_count(self) -> None:
        gov = AutonomousGovernance()
        gov.record_error("t-001", "auditee_response", "error")
        gov.record_error("t-001", "auditee_response", "error")
        gov.clear_error_count("t-001", "auditee_response")
        # リセット後は閾値に達しない
        for i in range(4):
            result = gov.record_error("t-001", "auditee_response", f"error-{i}")
            assert result is False

    def test_get_logs(self) -> None:
        gov = AutonomousGovernance()
        for i in range(3):
            gov.record_decision(
                decision_id=f"d-{i:03d}",
                tenant_id="t-001",
                agent_name="auditee_response",
                decision=self._make_decision(),
            )
        gov.record_decision(
            decision_id="d-other",
            tenant_id="t-002",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        logs = gov.get_logs("t-001")
        assert len(logs) == 3

    def test_get_logs_filtered_by_agent(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        gov.record_decision(
            decision_id="d-002",
            tenant_id="t-001",
            agent_name="auditee_prep",
            decision=self._make_decision(),
        )
        logs = gov.get_logs("t-001", agent_name="auditee_response")
        assert len(logs) == 1

    def test_get_pending_reviews(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        pending = gov.get_pending_reviews("t-001")
        assert len(pending) == 1

    def test_mark_reviewed(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        result = gov.mark_reviewed("d-001", "問題なし")
        assert result is True
        pending = gov.get_pending_reviews("t-001")
        assert len(pending) == 0

    def test_mark_reviewed_not_found(self) -> None:
        gov = AutonomousGovernance()
        result = gov.mark_reviewed("nonexistent")
        assert result is False

    def test_flag_for_review(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        result = gov.flag_for_review("d-001", "要確認")
        assert result is True
        stats = gov.get_stats("t-001")
        assert stats.flagged_for_review == 1

    def test_flag_for_review_not_found(self) -> None:
        gov = AutonomousGovernance()
        result = gov.flag_for_review("nonexistent")
        assert result is False

    def test_check_anomalous_pattern_empty(self) -> None:
        gov = AutonomousGovernance()
        anomalies = gov.check_anomalous_pattern("t-001")
        assert anomalies == []

    def test_check_anomalous_pattern_high_auto_rate(self) -> None:
        gov = AutonomousGovernance()
        for i in range(12):
            gov.record_decision(
                decision_id=f"d-{i:03d}",
                tenant_id="t-001",
                agent_name="auditee_response",
                decision=self._make_decision(approved=True, confidence=0.95),
            )
        anomalies = gov.check_anomalous_pattern("t-001")
        assert any("自動承認率" in a for a in anomalies)

    def test_check_anomalous_pattern_low_confidence(self) -> None:
        gov = AutonomousGovernance()
        for i in range(12):
            gov.record_decision(
                decision_id=f"d-{i:03d}",
                tenant_id="t-001",
                agent_name="auditee_response",
                decision=self._make_decision(approved=False, confidence=0.5),
            )
        anomalies = gov.check_anomalous_pattern("t-001")
        assert any("平均信頼度" in a for a in anomalies)

    def test_get_agent_summary(self) -> None:
        gov = AutonomousGovernance()
        summary = gov.get_agent_summary()
        assert len(summary) == 14
        assert all("agent_name" in s for s in summary)
        assert all("risk_tier" in s for s in summary)

    def test_stats_decisions_by_tier(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        stats = gov.get_stats("t-001")
        assert "medium" in stats.decisions_by_tier

    def test_stats_decisions_by_agent(self) -> None:
        gov = AutonomousGovernance()
        gov.record_decision(
            decision_id="d-001",
            tenant_id="t-001",
            agent_name="auditee_response",
            decision=self._make_decision(),
        )
        stats = gov.get_stats("t-001")
        assert "auditee_response" in stats.decisions_by_agent
