"""Controls Monitor Agent テスト"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.auditee.controls_monitor import ControlsMonitorAgent
from src.agents.state import AuditeeState


@pytest.fixture
def monitor_agent(mock_llm_gateway: MagicMock) -> ControlsMonitorAgent:
    return ControlsMonitorAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestControlsMonitorAgent:
    """統制モニタリングAgentのユニットテスト"""

    def test_agent_name(self, monitor_agent: ControlsMonitorAgent) -> None:
        assert monitor_agent.agent_name == "auditee_controls_monitor"

    async def test_execute_monitoring(self, monitor_agent: ControlsMonitorAgent) -> None:
        """モニタリング実行テスト"""
        from src.llm_gateway.providers.base import LLMResponse

        monitor_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content=(
                    '{"controls_assessment": [{"control_id": "CTL-001",'
                    ' "status": "effective", "compliance_rate": 0.95}],'
                    ' "overall_score": 0.88, "recommendations": []}'
                ),
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=200,
                output_tokens=100,
                total_tokens=300,
                cost_usd=0.002,
                latency_ms=800.0,
            )
        )

        state = AuditeeState(
            tenant_id=str(uuid4()),
            department="経理部",
            current_phase="monitoring",
        )

        result = await monitor_agent.execute(state)

        assert result.current_agent == "auditee_controls_monitor"
        assert isinstance(result.controls_status, list)

    async def test_execute_with_deficiency(self, monitor_agent: ControlsMonitorAgent) -> None:
        """不備検出時のテスト"""
        from src.llm_gateway.providers.base import LLMResponse

        monitor_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content=(
                    '{"controls_assessment": [{"control_id": "CTL-002",'
                    ' "status": "deficient", "compliance_rate": 0.5,'
                    ' "deficiency_type": "significant"}],'
                    ' "overall_score": 0.5, "recommendations": ["即時改善が必要"]}'
                ),
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=200,
                output_tokens=100,
                total_tokens=300,
                cost_usd=0.002,
                latency_ms=800.0,
            )
        )

        state = AuditeeState(
            tenant_id=str(uuid4()),
            department="購買部",
        )

        result = await monitor_agent.execute(state)
        assert result.current_agent == "auditee_controls_monitor"

    def test_infer_category(self, monitor_agent: ControlsMonitorAgent) -> None:
        """カテゴリ推定テスト"""
        assert monitor_agent._infer_category("購買承認フロー", "") == "approval"
        assert monitor_agent._infer_category("アクセス権限管理", "") == "access"
        assert monitor_agent._infer_category("取引仕訳確認", "") == "transaction"
        assert monitor_agent._infer_category("ITシステムバックアップ", "") == "it_general"
        assert monitor_agent._infer_category("不明な統制", "") == "other"
