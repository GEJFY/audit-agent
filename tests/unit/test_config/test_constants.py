"""Constants テスト"""

import pytest

from src.config.constants import (
    AGENT_CONFIDENCE_THRESHOLDS,
    API_VERSION,
    CONFIDENCE_THRESHOLD,
    DIALOGUE_TIMEOUT_HOURS,
    EVIDENCE_MAX_SIZE_MB,
    MAX_RETRY_ATTEMPTS,
    AgentMode,
    AuditeeAgentType,
    AuditorAgentType,
    ControlTestResult,
    DialogueMessageType,
    EscalationReason,
    FindingStatus,
    ProjectStatus,
    RiskLevel,
    UserRole,
)


@pytest.mark.unit
class TestUserRole:
    def test_all_roles(self) -> None:
        roles = list(UserRole)
        assert len(roles) == 6
        assert UserRole.ADMIN in roles
        assert UserRole.AUDITOR in roles
        assert UserRole.EXECUTIVE in roles

    def test_str_values(self) -> None:
        assert str(UserRole.ADMIN) == "admin"
        assert str(UserRole.AUDITOR) == "auditor"


@pytest.mark.unit
class TestProjectStatus:
    def test_all_statuses(self) -> None:
        statuses = list(ProjectStatus)
        assert len(statuses) == 6
        assert ProjectStatus.DRAFT in statuses
        assert ProjectStatus.CLOSED in statuses

    def test_lifecycle_order(self) -> None:
        """ライフサイクル順序"""
        expected = ["draft", "planning", "fieldwork", "reporting", "follow_up", "closed"]
        actual = [s.value for s in ProjectStatus]
        assert actual == expected


@pytest.mark.unit
class TestAuditorAgentType:
    def test_count(self) -> None:
        assert len(list(AuditorAgentType)) == 8

    def test_orchestrator_exists(self) -> None:
        assert AuditorAgentType.ORCHESTRATOR in list(AuditorAgentType)


@pytest.mark.unit
class TestAuditeeAgentType:
    def test_count(self) -> None:
        assert len(list(AuditeeAgentType)) == 6

    def test_response_exists(self) -> None:
        assert AuditeeAgentType.RESPONSE in list(AuditeeAgentType)


@pytest.mark.unit
class TestDialogueMessageType:
    def test_count(self) -> None:
        assert len(list(DialogueMessageType)) == 8

    def test_question_answer(self) -> None:
        assert DialogueMessageType.QUESTION in list(DialogueMessageType)
        assert DialogueMessageType.ANSWER in list(DialogueMessageType)


@pytest.mark.unit
class TestRiskLevel:
    def test_count(self) -> None:
        assert len(list(RiskLevel)) == 5

    def test_severity_order(self) -> None:
        expected = ["critical", "high", "medium", "low", "info"]
        actual = [r.value for r in RiskLevel]
        assert actual == expected


@pytest.mark.unit
class TestFindingStatus:
    def test_count(self) -> None:
        assert len(list(FindingStatus)) == 5
        assert FindingStatus.DRAFT in list(FindingStatus)
        assert FindingStatus.CLOSED in list(FindingStatus)


@pytest.mark.unit
class TestEscalationReason:
    def test_low_confidence_exists(self) -> None:
        assert EscalationReason.LOW_CONFIDENCE in list(EscalationReason)

    def test_high_risk_exists(self) -> None:
        assert EscalationReason.HIGH_RISK_DETECTED in list(EscalationReason)


@pytest.mark.unit
class TestAgentMode:
    def test_all_modes(self) -> None:
        modes = list(AgentMode)
        assert len(modes) == 3
        assert AgentMode.AUDIT in modes
        assert AgentMode.ASSIST in modes
        assert AgentMode.AUTONOMOUS in modes


@pytest.mark.unit
class TestControlTestResult:
    def test_all_results(self) -> None:
        results = list(ControlTestResult)
        assert len(results) == 4
        assert ControlTestResult.EFFECTIVE in results
        assert ControlTestResult.INEFFECTIVE in results


@pytest.mark.unit
class TestGlobalConstants:
    def test_confidence_threshold(self) -> None:
        assert CONFIDENCE_THRESHOLD == 0.75

    def test_max_retry_attempts(self) -> None:
        assert MAX_RETRY_ATTEMPTS == 3

    def test_evidence_max_size(self) -> None:
        assert EVIDENCE_MAX_SIZE_MB == 50

    def test_dialogue_timeout(self) -> None:
        assert DIALOGUE_TIMEOUT_HOURS == 24

    def test_api_version(self) -> None:
        assert API_VERSION == "v1"

    def test_agent_confidence_thresholds(self) -> None:
        assert isinstance(AGENT_CONFIDENCE_THRESHOLDS, dict)
        assert len(AGENT_CONFIDENCE_THRESHOLDS) > 0
        # 全値が0-1の範囲
        for key, value in AGENT_CONFIDENCE_THRESHOLDS.items():
            assert 0.0 <= value <= 1.0, f"{key}: {value} is out of range"
