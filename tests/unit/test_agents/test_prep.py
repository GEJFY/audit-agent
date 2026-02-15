"""PrepAgent テスト"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.auditee.prep import PrepAgent
from src.agents.state import AuditeeState
from src.llm_gateway.providers.base import LLMResponse


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> PrepAgent:
    a = PrepAgent(llm_gateway=mock_llm_gateway)
    a._audit_trail = MagicMock()
    return a


def _make_llm_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="claude-sonnet-4-5-20250929",
        provider="anthropic",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_usd=0.001,
        latency_ms=500.0,
    )


@pytest.mark.unit
class TestPrepAgent:
    def test_agent_name(self, agent: PrepAgent) -> None:
        assert agent.agent_name == "auditee_prep"

    async def test_execute_generates_questions(self, agent: PrepAgent) -> None:
        """想定質問生成"""
        questions = ["Q1: 承認プロセスの概要", "Q2: 例外処理の手順"]
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(json.dumps(questions)))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)

        assert len(result.predicted_questions) == 2
        assert result.current_phase == "preparing"
        assert result.current_agent == "auditee_prep"

    async def test_execute_generates_checklist(self, agent: PrepAgent) -> None:
        """チェックリスト生成"""
        questions = ["Q1", "Q2", "Q3"]
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(json.dumps(questions)))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)

        assert "items" in result.prep_checklist
        assert len(result.prep_checklist["items"]) == 3
        assert result.prep_checklist["completion_rate"] == 0.0
        # 各アイテムはpendingステータス
        for item in result.prep_checklist["items"]:
            assert item["status"] == "pending"

    async def test_question_json_parse_error(self, agent: PrepAgent) -> None:
        """JSONパースエラー → 単一要素リストにフォールバック"""
        agent._llm.generate = AsyncMock(return_value=_make_llm_response("これはJSONではない回答です"))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)
        assert len(result.predicted_questions) == 1
        assert result.predicted_questions[0] == "これはJSONではない回答です"

    async def test_checklist_truncates_to_10(self, agent: PrepAgent) -> None:
        """チェックリストは最大10件"""
        questions = [f"Q{i}" for i in range(15)]
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(json.dumps(questions)))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)
        assert len(result.prep_checklist["items"]) == 10

    async def test_fast_model_used(self, agent: PrepAgent) -> None:
        """use_fast_model=Trueが渡される"""
        questions = ["Q1"]
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(json.dumps(questions)))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        await agent.execute(state)

        call_kwargs = agent._llm.generate.call_args
        assert call_kwargs.kwargs.get("use_fast_model") is True

    async def test_past_audits_in_prompt(self, agent: PrepAgent) -> None:
        """過去の監査情報がプロンプトに含まれる"""
        questions = ["Q1"]
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(json.dumps(questions)))
        state = AuditeeState(
            tenant_id="t-001",
            department="経理部",
            metadata={"past_audits": [{"year": 2025, "findings": 3}]},
        )
        await agent.execute(state)
        call_args = agent._llm.generate.call_args
        assert "経理部" in call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")
