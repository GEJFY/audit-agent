"""Response Agent テスト"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.agents.auditee.response import ResponseAgent
from src.agents.state import AuditeeState


@pytest.fixture
def response_agent(mock_llm_gateway: MagicMock) -> ResponseAgent:
    return ResponseAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestResponseAgent:
    """回答Agentのユニットテスト"""

    def test_agent_name(self, response_agent: ResponseAgent) -> None:
        assert response_agent.agent_name == "auditee_response"

    async def test_execute_with_question(
        self,
        response_agent: ResponseAgent,
        sample_dialogue_question: dict,
    ) -> None:
        """質問に対する回答生成テスト"""
        from src.llm_gateway.providers.base import LLMResponse

        response_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"response_draft": "購買承認フローは3段階制です。", "confidence": 0.82, "referenced_documents": ["購買規程 v3.0"], "evidence_to_attach": ["承認フロー図"], "clarification_needed": []}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=300,
                output_tokens=150,
                total_tokens=450,
                cost_usd=0.003,
                latency_ms=1200.0,
            )
        )

        state = AuditeeState(
            tenant_id="test-tenant",
            department="購買部",
            incoming_questions=[sample_dialogue_question],
        )

        result = await response_agent.execute(state)

        assert result.current_agent == "auditee_response"
        assert result.current_phase == "responding"
        assert len(result.drafted_responses) == 1

    async def test_execute_no_questions(
        self, response_agent: ResponseAgent
    ) -> None:
        """質問なしの実行テスト"""
        state = AuditeeState(
            tenant_id="test-tenant",
            department="経理部",
            incoming_questions=[],
        )

        result = await response_agent.execute(state)

        assert len(result.drafted_responses) == 0
