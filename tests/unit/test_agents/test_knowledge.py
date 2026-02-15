"""Knowledge Agent テスト"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.auditor.knowledge import KnowledgeAgent
from src.agents.state import AuditorState


@pytest.fixture
def knowledge_agent(mock_llm_gateway: MagicMock) -> KnowledgeAgent:
    return KnowledgeAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestKnowledgeAgent:
    """知識検索Agentのユニットテスト"""

    def test_agent_name(self, knowledge_agent: KnowledgeAgent) -> None:
        assert knowledge_agent.agent_name == "auditor_knowledge"

    async def test_execute_with_questions(self, knowledge_agent: KnowledgeAgent) -> None:
        """質問ありでの実行テスト"""
        from src.llm_gateway.providers.base import LLMResponse

        knowledge_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content=(
                    '{"answer": "J-SOX法では内部統制報告書の提出が義務付けられています",'
                    ' "references": ["J-SOX基準 第5条"], "confidence": 0.9}'
                ),
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=300,
                output_tokens=150,
                total_tokens=450,
                cost_usd=0.003,
                latency_ms=1200.0,
            )
        )

        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            pending_questions=[
                {
                    "id": "q-001",
                    "content": "J-SOX法における内部統制報告書の提出要件は？",
                    "topic": "j-sox",
                }
            ],
        )

        result = await knowledge_agent.execute(state)

        assert result.current_agent == "auditor_knowledge"

    async def test_execute_no_questions(self, knowledge_agent: KnowledgeAgent) -> None:
        """質問なしでの実行テスト"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            pending_questions=[],
        )

        result = await knowledge_agent.execute(state)
        assert result.current_agent == "auditor_knowledge"

    async def test_generate_direct_answer(self, knowledge_agent: KnowledgeAgent) -> None:
        """直接回答生成テスト（ベクトル検索結果なし時）"""
        from src.llm_gateway.providers.base import LLMResponse

        knowledge_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"answer": "一般的に監査基準では..."}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.001,
                latency_ms=500.0,
            )
        )

        answer = await knowledge_agent._generate_direct_answer(
            query="監査の基本原則は？",
        )

        assert answer is not None
        assert isinstance(answer, dict)
        assert answer.get("search_method") == "direct_llm"
