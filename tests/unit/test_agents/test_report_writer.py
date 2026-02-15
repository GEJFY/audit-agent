"""ReportWriterAgent テスト"""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.agents.state import AuditorState
from src.llm_gateway.providers.base import LLMResponse


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> "ReportWriterAgent":  # noqa: F821
    from src.agents.auditor.report_writer import ReportWriterAgent

    a = ReportWriterAgent(llm_gateway=mock_llm_gateway)
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
class TestReportWriterAgent:
    def test_agent_name(self, agent: "ReportWriterAgent") -> None:  # noqa: F821
        assert agent.agent_name == "auditor_report_writer"

    async def test_execute_report_generation(self, agent: "ReportWriterAgent") -> None:  # noqa: F821
        """報告書生成"""
        report_json = json.dumps(
            {
                "executive_summary": "テストサマリー",
                "findings_detail": [{"finding_ref": "F-001", "title": "テスト検出事項"}],
                "overall_opinion": "改善の余地あり",
                "confidence": 0.8,
            }
        )
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(report_json))

        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            findings=[{"id": "f1", "description": "テスト"}],
            test_results=[{"result": "effective"}],
        )
        result = await agent.execute(state)

        assert result.report["executive_summary"] == "テストサマリー"
        assert result.requires_approval is True
        assert result.approval_context["type"] == "report"
        assert result.current_agent == "auditor_report_writer"

    async def test_always_requires_approval(self, agent: "ReportWriterAgent") -> None:  # noqa: F821
        """報告書は常に承認必要"""
        report_json = json.dumps({"executive_summary": "テスト", "confidence": 0.99})
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(report_json))

        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert result.requires_approval is True

    async def test_json_parse_error(self, agent: "ReportWriterAgent") -> None:  # noqa: F821
        """JSONパースエラー時のフォールバック"""
        agent._llm.generate = AsyncMock(return_value=_make_llm_response("これはJSONではありません"))
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert "raw_content" in result.report
        assert result.report["confidence"] == 0.5

    async def test_approval_context(self, agent: "ReportWriterAgent") -> None:  # noqa: F821
        """承認コンテキスト設定"""
        report_json = json.dumps({"executive_summary": "テスト"})
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(report_json))

        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        result = await agent.execute(state)
        assert result.approval_context["reason"] == "監査報告書の最終承認"

    async def test_record_decision_called(self, agent: "ReportWriterAgent") -> None:  # noqa: F821
        """監査証跡記録"""
        report_json = json.dumps({"executive_summary": "テスト", "confidence": 0.85})
        agent._llm.generate = AsyncMock(return_value=_make_llm_response(report_json))

        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
        )
        await agent.execute(state)
        assert agent._audit_trail.record_agent_decision.called
