"""RiskAlertAgent テスト"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.auditee.risk_alert import RiskAlertAgent
from src.agents.state import AuditeeState
from src.llm_gateway.providers.base import LLMResponse


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> RiskAlertAgent:
    a = RiskAlertAgent(llm_gateway=mock_llm_gateway)
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
class TestRiskAlertAgent:
    def test_agent_name(self, agent: RiskAlertAgent) -> None:
        assert agent.agent_name == "auditee_risk_alert"

    async def test_execute_no_alerts(self, agent: RiskAlertAgent) -> None:
        """全カテゴリでアラートなし"""
        agent._llm.generate = AsyncMock(return_value=_make_llm_response("[]"))

        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)

        assert result.risk_alerts == []
        assert result.current_agent == "auditee_risk_alert"

    async def test_execute_with_alerts(self, agent: RiskAlertAgent) -> None:
        """アラート検出"""
        alert = json.dumps(
            [
                {
                    "type": "financial",
                    "severity": "high",
                    "title": "異常仕訳",
                    "description": "高額仕訳を検出",
                    "recommended_action": "調査実施",
                }
            ]
        )
        empty = "[]"
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(alert),  # financial
                _make_llm_response(empty),  # operational
                _make_llm_response(empty),  # it
                _make_llm_response(empty),  # compliance
                _make_llm_response(empty),  # external
            ]
        )
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)

        assert len(result.risk_alerts) == 1
        assert result.risk_alerts[0]["title"] == "異常仕訳"

    async def test_critical_alert_escalation(self, agent: RiskAlertAgent) -> None:
        """重大リスクの自動エスカレーション"""
        critical_alert = json.dumps(
            [
                {
                    "type": "financial",
                    "severity": "critical",
                    "title": "不正仕訳",
                    "description": "重大",
                }
            ]
        )
        empty = "[]"
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(critical_alert),
                _make_llm_response(empty),
                _make_llm_response(empty),
                _make_llm_response(empty),
                _make_llm_response(empty),
            ]
        )
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)

        assert result.risk_alerts[0]["escalate_to_auditor"] is True

    async def test_high_alert_escalation(self, agent: RiskAlertAgent) -> None:
        """highリスクもエスカレーション"""
        high_alert = json.dumps([{"type": "it", "severity": "high", "title": "不正アクセス"}])
        empty = "[]"
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(empty),
                _make_llm_response(empty),
                _make_llm_response(high_alert),
                _make_llm_response(empty),
                _make_llm_response(empty),
            ]
        )
        state = AuditeeState(tenant_id="t-001", department="IT部")
        result = await agent.execute(state)
        assert result.risk_alerts[0]["escalate_to_auditor"] is True

    async def test_medium_alert_no_escalation(self, agent: RiskAlertAgent) -> None:
        """medium/lowリスクはエスカレーションなし"""
        medium_alert = json.dumps(
            [
                {
                    "type": "operational",
                    "severity": "medium",
                    "title": "処理遅延",
                }
            ]
        )
        empty = "[]"
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(empty),
                _make_llm_response(medium_alert),
                _make_llm_response(empty),
                _make_llm_response(empty),
                _make_llm_response(empty),
            ]
        )
        state = AuditeeState(tenant_id="t-001", department="営業部")
        result = await agent.execute(state)
        assert "escalate_to_auditor" not in result.risk_alerts[0]

    async def test_json_parse_error_returns_empty(self, agent: RiskAlertAgent) -> None:
        """JSONパースエラーは空リスト"""
        agent._llm.generate = AsyncMock(return_value=_make_llm_response("Invalid JSON response"))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        result = await agent.execute(state)
        assert result.risk_alerts == []

    async def test_five_categories_scanned(self, agent: RiskAlertAgent) -> None:
        """5カテゴリ全てスキャンされる"""
        agent._llm.generate = AsyncMock(return_value=_make_llm_response("[]"))
        state = AuditeeState(tenant_id="t-001", department="経理部")
        await agent.execute(state)
        assert agent._llm.generate.call_count == 5

    async def test_multiple_alerts_per_category(self, agent: RiskAlertAgent) -> None:
        """1カテゴリから複数アラート"""
        alerts = json.dumps(
            [
                {"type": "compliance", "severity": "high", "title": "A"},
                {"type": "compliance", "severity": "low", "title": "B"},
            ]
        )
        empty = "[]"
        agent._llm.generate = AsyncMock(
            side_effect=[
                _make_llm_response(empty),
                _make_llm_response(empty),
                _make_llm_response(empty),
                _make_llm_response(alerts),
                _make_llm_response(empty),
            ]
        )
        state = AuditeeState(tenant_id="t-001", department="法務部")
        result = await agent.execute(state)
        assert len(result.risk_alerts) == 2
