"""ControlsTesterAgent テスト"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.auditor.controls_tester import ControlsTesterAgent
from src.agents.state import AuditorState
from src.llm_gateway.providers.base import LLMResponse


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> ControlsTesterAgent:
    a = ControlsTesterAgent(llm_gateway=mock_llm_gateway)
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
class TestControlsTesterAgent:
    def test_agent_name(self, agent: ControlsTesterAgent) -> None:
        assert agent.agent_name == "auditor_controls_tester"

    def test_agent_description(self, agent: ControlsTesterAgent) -> None:
        assert agent.agent_description != ""

    async def test_execute_empty_procedures(self, agent: ControlsTesterAgent) -> None:
        """テスト手続なしの場合"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={},
        )
        result = await agent.execute(state)
        assert result.test_results == []
        assert result.current_agent == "auditor_controls_tester"
        assert result.metadata["test_summary"]["total_tests"] == 0

    async def test_execute_with_procedures(self, agent: ControlsTesterAgent) -> None:
        """テスト手続ありの場合"""
        agent._llm.generate = AsyncMock(
            return_value=_make_llm_response(
                '{"procedure": "承認テスト", "result": "effective", '
                '"sample_tested": 25, "exceptions_found": 0, '
                '"details": "問題なし", "confidence": 0.9}'
            )
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={"test_procedures": [{"name": "承認テスト"}]},
        )
        result = await agent.execute(state)
        assert len(result.test_results) == 1
        assert result.test_results[0]["result"] == "effective"
        assert result.current_agent == "auditor_controls_tester"

    async def test_execute_multiple_procedures(self, agent: ControlsTesterAgent) -> None:
        """複数テスト手続"""
        agent._llm.generate = AsyncMock(
            return_value=_make_llm_response('{"procedure": "テスト", "result": "effective", "confidence": 0.85}')
        )
        procedures = [{"name": f"テスト{i}"} for i in range(3)]
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={"test_procedures": procedures},
        )
        result = await agent.execute(state)
        assert len(result.test_results) == 3

    async def test_json_parse_error_fallback(self, agent: ControlsTesterAgent) -> None:
        """JSONパースエラー時のフォールバック"""
        agent._llm.generate = AsyncMock(return_value=_make_llm_response("Invalid JSON response"))
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={"test_procedures": [{"name": "テスト"}]},
        )
        result = await agent.execute(state)
        assert result.test_results[0]["result"] == "not_tested"
        assert result.test_results[0]["confidence"] == 0.3

    async def test_record_decision_called(self, agent: ControlsTesterAgent) -> None:
        """監査証跡の記録"""
        agent._llm.generate = AsyncMock(
            return_value=_make_llm_response(
                '{"procedure": "テスト", "result": "effective", "confidence": 0.9, "details": "ok"}'
            )
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={"test_procedures": [{"name": "テスト"}]},
        )
        await agent.execute(state)
        assert agent._audit_trail.record_agent_decision.called

    async def test_summarize_results_satisfactory(self, agent: ControlsTesterAgent) -> None:
        """サマリー: satisfactory判定（effective率 > 80%）"""
        results = [
            {"result": "effective"},
            {"result": "effective"},
            {"result": "effective"},
            {"result": "effective"},
            {"result": "effective"},
        ]
        summary = await agent._summarize_results(results)
        assert summary["total_tests"] == 5
        assert summary["effective"] == 5
        assert summary["overall_assessment"] == "satisfactory"

    async def test_summarize_results_needs_improvement(self, agent: ControlsTesterAgent) -> None:
        """サマリー: needs_improvement判定（effective率 <= 80%）"""
        results = [
            {"result": "effective"},
            {"result": "ineffective"},
            {"result": "ineffective"},
        ]
        summary = await agent._summarize_results(results)
        assert summary["overall_assessment"] == "needs_improvement"

    async def test_string_procedure(self, agent: ControlsTesterAgent) -> None:
        """文字列形式のテスト手続"""
        agent._llm.generate = AsyncMock(
            return_value=_make_llm_response('{"procedure": "テスト", "result": "effective", "confidence": 0.8}')
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={"test_procedures": ["承認プロセスの有効性テスト"]},
        )
        result = await agent.execute(state)
        assert len(result.test_results) == 1
