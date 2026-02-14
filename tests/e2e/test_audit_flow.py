"""E2E 監査フローテスト"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.agents.state import AuditorState, AuditeeState


@pytest.mark.e2e
class TestAuditFlowE2E:
    """監査フローのE2Eテスト"""

    async def test_auditor_agent_chain(self, mock_llm_gateway: MagicMock) -> None:
        """監査側Agentチェーン実行テスト

        planner → anomaly_detective の一連のフローを
        モック環境で実行し、Stateが正しく伝搬されることを検証。
        """
        from src.llm_gateway.providers.base import LLMResponse
        from src.agents.auditor.planner import PlannerAgent
        from src.agents.auditor.anomaly_detective import AnomalyDetectiveAgent

        plan_response = LLMResponse(
            content='{"risk_areas": ["revenue"], "audit_scope": "Q3-Q4", "priority": "high"}',
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
            cost_usd=0.002,
            latency_ms=800.0,
        )

        anomaly_response = LLMResponse(
            content='{"anomalies": [{"transaction_id": "JE-003", "anomaly_type": "amount", "severity": "high", "description": "高額期末仕訳", "confidence": 0.85}], "summary": "1件検出"}',
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            input_tokens=300,
            output_tokens=150,
            total_tokens=450,
            cost_usd=0.003,
            latency_ms=1200.0,
        )

        # Step 1: Planner
        mock_llm_gateway.generate = AsyncMock(return_value=plan_response)
        planner = PlannerAgent(llm_gateway=mock_llm_gateway)
        state = AuditorState(
            project_id="proj-001",
            tenant_id="tenant-001",
        )

        state = await planner.execute(state)
        assert state.current_agent == "auditor_planner"
        assert state.current_phase == "planning"

        # Step 2: Anomaly Detective
        mock_llm_gateway.generate = AsyncMock(return_value=anomaly_response)
        detective = AnomalyDetectiveAgent(llm_gateway=mock_llm_gateway)
        state.metadata["collected_data"] = [
            {"id": "JE-003", "amount": 50_000_000, "account_code": "1100"},
        ]

        state = await detective.execute(state)
        assert state.current_agent == "auditor_anomaly_detective"

    async def test_auditee_response_flow(self, mock_llm_gateway: MagicMock) -> None:
        """被監査側回答フローテスト

        質問受信 → 回答生成 の基本フロー。
        """
        from src.llm_gateway.providers.base import LLMResponse
        from src.agents.auditee.response import ResponseAgent

        response_llm = LLMResponse(
            content='{"response_draft": "購買承認は3段階制です。", "confidence": 0.85, "referenced_documents": ["購買規程"], "evidence_to_attach": [], "clarification_needed": []}',
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            input_tokens=300,
            output_tokens=150,
            total_tokens=450,
            cost_usd=0.003,
            latency_ms=1000.0,
        )

        mock_llm_gateway.generate = AsyncMock(return_value=response_llm)

        agent = ResponseAgent(llm_gateway=mock_llm_gateway)
        state = AuditeeState(
            tenant_id="tenant-002",
            department="購買部",
            incoming_questions=[
                {
                    "id": "q-001",
                    "content": "購買承認フローの詳細を教えてください",
                    "from_agent": "auditor_controls_tester",
                }
            ],
        )

        result = await agent.execute(state)

        assert result.current_agent == "auditee_response"
        assert result.current_phase == "responding"
        assert len(result.drafted_responses) == 1

    async def test_dialogue_round_trip(self) -> None:
        """対話ラウンドトリップテスト

        監査側 → 被監査側 → 監査側 のメッセージ往復。
        """
        from uuid import uuid4
        from src.dialogue.bus import DialogueBus
        from src.dialogue.protocol import QuestionMessage, AnswerMessage

        bus = DialogueBus()

        auditor_tenant = uuid4()
        auditee_tenant = uuid4()

        # 質問送信
        question = QuestionMessage(
            from_tenant_id=auditor_tenant,
            to_tenant_id=auditee_tenant,
            from_agent="auditor_controls_tester",
            content="Q3の承認記録を提出してください。",
            priority="high",
        )
        sent_q = await bus.send(question)

        assert sent_q.thread_id is not None

        # 回答送信
        answer = AnswerMessage(
            from_tenant_id=auditee_tenant,
            to_tenant_id=auditor_tenant,
            from_agent="auditee_response",
            content="Q3の承認記録を添付いたします。全件の承認が完了しています。",
            confidence=0.9,
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        sent_a = await bus.send(answer)

        # スレッド確認
        thread = bus.get_thread(sent_q.thread_id)
        assert len(thread) == 2
        assert thread[0].content == question.content
        assert thread[1].content == answer.content
