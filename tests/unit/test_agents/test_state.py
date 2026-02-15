"""State クラステスト"""

import pytest

from src.agents.state import AgentMessage, AuditeeState, AuditorState


@pytest.mark.unit
class TestAgentMessage:
    """AgentMessageテスト"""

    def test_required_fields(self) -> None:
        msg = AgentMessage(role="human", content="テスト")
        assert msg.role == "human"
        assert msg.content == "テスト"

    def test_metadata_default(self) -> None:
        msg = AgentMessage(role="ai", content="回答")
        assert msg.metadata == {}

    def test_metadata_custom(self) -> None:
        msg = AgentMessage(role="tool", content="結果", metadata={"key": "val"})
        assert msg.metadata["key"] == "val"


@pytest.mark.unit
class TestAuditorState:
    """AuditorStateテスト"""

    def test_defaults(self) -> None:
        state = AuditorState()
        assert state.project_id == ""
        assert state.tenant_id == ""
        assert state.agent_mode == "audit"
        assert state.current_phase == "init"
        assert state.current_agent == ""
        assert state.requires_approval is False

    def test_mutable_defaults_independent(self) -> None:
        """Field(default_factory)による独立性"""
        s1 = AuditorState()
        s2 = AuditorState()
        s1.findings.append({"id": "f1"})
        assert len(s2.findings) == 0

    def test_field_assignment(self) -> None:
        state = AuditorState(
            project_id="p-001",
            tenant_id="t-001",
            current_phase="fieldwork",
        )
        assert state.project_id == "p-001"
        assert state.current_phase == "fieldwork"

    def test_dict_fields(self) -> None:
        state = AuditorState()
        assert isinstance(state.risk_assessment, dict)
        assert isinstance(state.audit_plan, dict)
        assert isinstance(state.report, dict)
        assert isinstance(state.metadata, dict)

    def test_list_fields(self) -> None:
        state = AuditorState()
        assert isinstance(state.test_results, list)
        assert isinstance(state.anomalies, list)
        assert isinstance(state.findings, list)
        assert isinstance(state.errors, list)

    def test_approval_flow(self) -> None:
        state = AuditorState()
        state.requires_approval = True
        state.approval_context = {"type": "plan", "reason": "低信頼度"}
        assert state.requires_approval is True
        assert state.approval_context["type"] == "plan"


@pytest.mark.unit
class TestAuditeeState:
    """AuditeeStateテスト"""

    def test_defaults(self) -> None:
        state = AuditeeState()
        assert state.tenant_id == ""
        assert state.department == ""
        assert state.current_phase == "idle"
        assert state.current_agent == ""
        assert state.requires_approval is False

    def test_mutable_defaults_independent(self) -> None:
        s1 = AuditeeState()
        s2 = AuditeeState()
        s1.risk_alerts.append({"id": "a1"})
        assert len(s2.risk_alerts) == 0

    def test_field_assignment(self) -> None:
        state = AuditeeState(
            tenant_id="t-001",
            department="経理部",
            current_phase="responding",
        )
        assert state.department == "経理部"
        assert state.current_phase == "responding"

    def test_list_fields(self) -> None:
        state = AuditeeState()
        assert isinstance(state.incoming_questions, list)
        assert isinstance(state.drafted_responses, list)
        assert isinstance(state.evidence_search_results, list)
        assert isinstance(state.risk_alerts, list)
        assert isinstance(state.predicted_questions, list)

    def test_dict_fields(self) -> None:
        state = AuditeeState()
        assert isinstance(state.prep_checklist, dict)
        assert isinstance(state.metadata, dict)
