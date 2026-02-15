"""AuditeeOrchestrator テスト"""

from unittest.mock import MagicMock

import pytest

from src.agents.auditee.orchestrator import AuditeeOrchestrator
from src.agents.state import AuditeeState


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> AuditeeOrchestrator:
    return AuditeeOrchestrator(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestAuditeeOrchestrator:
    def test_agent_name(self, agent: AuditeeOrchestrator) -> None:
        assert agent.agent_name == "auditee_orchestrator"

    async def test_execute_no_questions(self, agent: AuditeeOrchestrator) -> None:
        """質問なし → idle"""
        state = AuditeeState(tenant_id="t-001", department="経理")
        result = await agent.execute(state)
        assert result.current_phase == "idle"
        assert result.current_agent == "auditee_orchestrator"

    async def test_execute_with_questions(self, agent: AuditeeOrchestrator) -> None:
        """質問あり → responding"""
        state = AuditeeState(
            tenant_id="t-001",
            department="経理",
            incoming_questions=[
                {"type": "question", "content": "承認フローの詳細"},
            ],
        )
        result = await agent.execute(state)
        assert result.current_phase == "responding"

    def test_routing_evidence_request(self, agent: AuditeeOrchestrator) -> None:
        result = agent._determine_routing({"type": "evidence_request"})
        assert result == "auditee_evidence_search"

    def test_routing_question(self, agent: AuditeeOrchestrator) -> None:
        result = agent._determine_routing({"type": "question"})
        assert result == "auditee_response"

    def test_routing_preparation(self, agent: AuditeeOrchestrator) -> None:
        result = agent._determine_routing({"type": "preparation"})
        assert result == "auditee_prep"

    def test_routing_general(self, agent: AuditeeOrchestrator) -> None:
        result = agent._determine_routing({"type": "general"})
        assert result == "auditee_response"

    def test_routing_unknown_type(self, agent: AuditeeOrchestrator) -> None:
        result = agent._determine_routing({"type": "unknown_type"})
        assert result == "auditee_response"

    def test_routing_no_type(self, agent: AuditeeOrchestrator) -> None:
        """typeフィールドなし → generalデフォルト"""
        result = agent._determine_routing({"content": "質問内容"})
        assert result == "auditee_response"
