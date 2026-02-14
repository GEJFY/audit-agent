"""Anomaly Detective Agent テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.auditor.anomaly_detective import AnomalyDetectiveAgent
from src.agents.state import AuditorState


@pytest.fixture
def anomaly_agent(mock_llm_gateway: MagicMock) -> AnomalyDetectiveAgent:
    return AnomalyDetectiveAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestAnomalyDetectiveAgent:
    """異常検知Agentのユニットテスト"""

    def test_agent_name(self, anomaly_agent: AnomalyDetectiveAgent) -> None:
        assert anomaly_agent.agent_name == "auditor_anomaly_detective"

    async def test_execute_empty_data(self, anomaly_agent: AnomalyDetectiveAgent) -> None:
        """空データでの実行テスト"""
        from src.llm_gateway.providers.base import LLMResponse

        # LLMの応答をモック
        anomaly_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"anomalies": [], "summary": "異常なし", "risk_assessment": "低リスク"}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.001,
                latency_ms=500.0,
            )
        )

        state = AuditorState(
            project_id="test-project",
            tenant_id="test-tenant",
            metadata={"collected_data": []},
        )

        result = await anomaly_agent.execute(state)

        assert result.current_agent == "auditor_anomaly_detective"
        assert isinstance(result.anomalies, list)

    async def test_execute_with_sample_data(
        self,
        anomaly_agent: AnomalyDetectiveAgent,
        sample_journal_entries: list,
    ) -> None:
        """サンプルデータでの実行テスト"""
        from src.llm_gateway.providers.base import LLMResponse

        anomaly_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content=(
                    '{"anomalies": [{"transaction_id": "JE-003", "anomaly_type": "amount",'
                    ' "severity": "high", "description": "異常に高額な期末調整仕訳",'
                    ' "confidence": 0.85}], "summary": "1件の異常検出"}'
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

        state = AuditorState(
            project_id="test-project",
            tenant_id="test-tenant",
            metadata={"collected_data": sample_journal_entries},
        )

        result = await anomaly_agent.execute(state)

        assert result.current_agent == "auditor_anomaly_detective"

    def test_promote_to_findings(self, anomaly_agent: AnomalyDetectiveAgent) -> None:
        """重大異常のFinding昇格テスト"""
        state = AuditorState(project_id="test", tenant_id="test-tenant")
        anomalies = [
            {"severity": "critical", "confidence": 0.9, "description": "重大な異常"},
            {"severity": "low", "confidence": 0.3, "description": "軽微な異常"},
            {"severity": "high", "confidence": 0.8, "description": "高リスク異常"},
        ]

        findings = anomaly_agent._promote_to_findings(anomalies, state)

        # critical + high で confidence >= 0.7 のみ昇格
        assert len(findings) == 2
        assert findings[0]["risk_level"] == "critical"
        assert findings[1]["risk_level"] == "high"
