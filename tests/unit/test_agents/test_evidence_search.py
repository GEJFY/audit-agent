"""Evidence Search Agent テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.auditee.evidence_search import EvidenceSearchAgent
from src.agents.state import AuditeeState


@pytest.fixture
def evidence_agent(mock_llm_gateway: MagicMock) -> EvidenceSearchAgent:
    return EvidenceSearchAgent(llm_gateway=mock_llm_gateway)


@pytest.mark.unit
class TestEvidenceSearchAgent:
    """証跡検索Agentのユニットテスト"""

    def test_agent_name(self, evidence_agent: EvidenceSearchAgent) -> None:
        assert evidence_agent.agent_name == "auditee_evidence_search"

    async def test_execute_with_evidence_queue(self, evidence_agent: EvidenceSearchAgent) -> None:
        """証跡キューありでの実行テスト"""
        from src.llm_gateway.providers.base import LLMResponse

        evidence_agent._llm.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"search_strategy": "parallel", "source_priority": ["sharepoint"]}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.001,
                latency_ms=500.0,
            )
        )

        state = AuditeeState(
            tenant_id="test-tenant",
            department="経理部",
            evidence_queue=[
                {
                    "description": "Q3承認記録",
                    "evidence_type": "approval_record",
                    "requested_by": "auditor_controls_tester",
                }
            ],
        )

        result = await evidence_agent.execute(state)

        assert result.current_agent == "auditee_evidence_search"
        assert result.current_phase == "searching"

    async def test_execute_empty_queue(self, evidence_agent: EvidenceSearchAgent) -> None:
        """空キューでの実行テスト"""
        state = AuditeeState(
            tenant_id="test-tenant",
            department="総務部",
            evidence_queue=[],
        )

        result = await evidence_agent.execute(state)
        assert len(result.evidence_search_results) == 0

    def test_classify_evidence_type_sharepoint(self, evidence_agent: EvidenceSearchAgent) -> None:
        """SharePoint証跡タイプ分類テスト"""
        # PDFドキュメント
        assert (
            evidence_agent._classify_evidence_type(
                {"name": "承認記録.pdf", "mime_type": "application/pdf"}, "sharepoint"
            )
            == "pdf_document"
        )

        # Excel
        assert (
            evidence_agent._classify_evidence_type({"name": "データ.xlsx", "mime_type": ""}, "sharepoint")
            == "spreadsheet"
        )

        # Word
        assert (
            evidence_agent._classify_evidence_type({"name": "契約書.docx", "mime_type": ""}, "sharepoint")
            == "word_document"
        )

    def test_classify_evidence_type_sap(self, evidence_agent: EvidenceSearchAgent) -> None:
        """SAP証跡タイプ分類テスト"""
        assert evidence_agent._classify_evidence_type({"module": "fi"}, "sap") == "journal_entry"
        assert evidence_agent._classify_evidence_type({"module": "mm"}, "sap") == "purchase_order"

    def test_classify_evidence_type_email(self, evidence_agent: EvidenceSearchAgent) -> None:
        """メール証跡タイプ分類テスト"""
        assert evidence_agent._classify_evidence_type({"has_attachments": True}, "email") == "email_with_attachment"
        assert evidence_agent._classify_evidence_type({"has_attachments": False}, "email") == "email"

    def test_calculate_relevance(self, evidence_agent: EvidenceSearchAgent) -> None:
        """関連度スコア計算テスト"""
        # 名前にクエリ語が含まれるアイテム → 高スコア
        item = {"name": "購買承認フロー記録", "subject": ""}
        score = evidence_agent._calculate_relevance(item, "購買承認フロー")
        assert score > 0.0

        # 無関係なアイテム → 低スコア
        item_low = {"name": "other_file.txt", "subject": ""}
        score_low = evidence_agent._calculate_relevance(item_low, "購買承認フロー")
        assert score_low <= score
