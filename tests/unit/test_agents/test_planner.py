"""PlannerAgent テスト"""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.auditor.planner import PlannerAgent
from src.agents.state import AuditorState
from src.llm_gateway.providers.base import LLMResponse


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> PlannerAgent:
    a = PlannerAgent(llm_gateway=mock_llm_gateway)
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
class TestPlannerAgent:
    def test_agent_name(self, agent: PlannerAgent) -> None:
        assert agent.agent_name == "auditor_planner"

    async def test_execute_full_flow(self, agent: PlannerAgent) -> None:
        """リスク評価→計画生成の全フロー"""
        risk_json = json.dumps(
            {
                "high_risk_areas": ["購買"],
                "risk_scores": {"購買": 0.8},
                "recommended_focus": "購買承認フロー",
            }
        )
        plan_json = json.dumps(
            {
                "scope": "購買プロセス",
                "objectives": ["承認フロー検証"],
                "methodology": "サンプリング",
                "test_procedures": [{"name": "承認テスト"}],
                "confidence": 0.85,
            }
        )
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(risk_json),
                _make_llm_response(plan_json),
            ]
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)

        assert result.risk_assessment["high_risk_areas"] == ["購買"]
        assert result.audit_plan["scope"] == "購買プロセス"
        assert result.current_agent == "auditor_planner"
        assert result.requires_approval is False  # confidence 0.85 > 0.75

    async def test_risk_assessment_json_error(self, agent: PlannerAgent) -> None:
        """リスク評価JSONパースエラー"""
        plan_json = json.dumps({"scope": "テスト", "confidence": 0.9})
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response("Invalid JSON for risk"),
                _make_llm_response(plan_json),
            ]
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert "raw_assessment" in result.risk_assessment
        assert result.risk_assessment["confidence"] == 0.5

    async def test_plan_generation_json_error(self, agent: PlannerAgent) -> None:
        """計画生成JSONパースエラー"""
        risk_json = json.dumps({"high_risk_areas": []})
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(risk_json),
                _make_llm_response("Invalid plan JSON"),
            ]
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert "raw_plan" in result.audit_plan
        assert result.audit_plan["confidence"] == 0.5

    async def test_escalation_on_low_confidence(self, agent: PlannerAgent) -> None:
        """低信頼度でエスカレーション"""
        risk_json = json.dumps({"high_risk_areas": []})
        plan_json = json.dumps({"scope": "テスト", "confidence": 0.3})
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(risk_json),
                _make_llm_response(plan_json),
            ]
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert result.requires_approval is True
        assert result.approval_context["type"] == "audit_plan"

    async def test_no_escalation_on_high_confidence(self, agent: PlannerAgent) -> None:
        """高信頼度でエスカレーションなし"""
        risk_json = json.dumps({"high_risk_areas": []})
        plan_json = json.dumps({"scope": "テスト", "confidence": 0.95})
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(risk_json),
                _make_llm_response(plan_json),
            ]
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert result.requires_approval is False

    async def test_record_decision_called(self, agent: PlannerAgent) -> None:
        """監査証跡記録"""
        risk_json = json.dumps({"high_risk_areas": []})
        plan_json = json.dumps({"scope": "テスト", "methodology": "分析", "confidence": 0.8})
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(risk_json),
                _make_llm_response(plan_json),
            ]
        )
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        await agent.execute(state)
        assert agent._audit_trail.record_agent_decision.called
