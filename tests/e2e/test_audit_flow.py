"""E2E 監査フローテスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.state import AuditeeState, AuditorState

# テスト用UUID文字列（record_decisionでUUID変換されるため正規UUIDが必要）
_TENANT_AUDITOR = "10000000-0000-0000-0000-000000000001"
_TENANT_AUDITEE = "20000000-0000-0000-0000-000000000002"
_PROJECT_001 = "40000000-0000-0000-0000-000000000001"
_PROJECT_E2E = "40000000-0000-0000-0000-e2e000000001"


@pytest.mark.e2e
class TestAuditFlowE2E:
    """監査フローのE2Eテスト"""

    async def test_auditor_agent_chain(self, mock_llm_gateway: MagicMock) -> None:
        """監査側Agentチェーン実行テスト

        planner → anomaly_detective の一連のフローを
        モック環境で実行し、Stateが正しく伝搬されることを検証。
        """
        from src.agents.auditor.anomaly_detective import AnomalyDetectiveAgent
        from src.agents.auditor.planner import PlannerAgent
        from src.llm_gateway.providers.base import LLMResponse

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
            content=(
                '{"anomalies": [{"transaction_id": "JE-003", "anomaly_type": "amount",'
                ' "severity": "high", "description": "高額期末仕訳",'
                ' "confidence": 0.85}], "summary": "1件検出"}'
            ),
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
            project_id=_PROJECT_001,
            tenant_id=_TENANT_AUDITOR,
        )

        state = await planner.execute(state)
        assert state.current_agent == "auditor_planner"

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
        from src.agents.auditee.response import ResponseAgent
        from src.llm_gateway.providers.base import LLMResponse

        response_llm = LLMResponse(
            content=(
                '{"response_draft": "購買承認は3段階制です。", "confidence": 0.85,'
                ' "referenced_documents": ["購買規程"],'
                ' "evidence_to_attach": [], "clarification_needed": []}'
            ),
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
            tenant_id=_TENANT_AUDITEE,
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
        from src.dialogue.protocol import AnswerMessage, QuestionMessage

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
        await bus.send(answer)

        # スレッド確認
        thread = bus.get_thread(sent_q.thread_id)
        assert len(thread) == 2
        assert thread[0].content == question.content
        assert thread[1].content == answer.content


@pytest.mark.e2e
class TestMultiAgentCoordination:
    """複数エージェント連携のE2Eテスト"""

    async def test_full_audit_cycle(self, mock_llm_gateway: MagicMock) -> None:
        """完全な監査サイクル: planner → controls_tester → report_writer"""
        from src.agents.auditor.controls_tester import ControlsTesterAgent
        from src.agents.auditor.planner import PlannerAgent
        from src.agents.auditor.report_writer import ReportWriterAgent
        from src.llm_gateway.providers.base import LLMResponse

        # Phase 1: 計画
        mock_llm_gateway.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"risk_areas": ["access_control", "financial_process"],'
                ' "audit_scope": "FY2025 Q4", "priority": "high",'
                ' "controls_to_test": ["AC-001", "FP-001"]}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=200,
                output_tokens=120,
                total_tokens=320,
                cost_usd=0.002,
                latency_ms=600.0,
            )
        )

        planner = PlannerAgent(llm_gateway=mock_llm_gateway)
        state = AuditorState(project_id=_PROJECT_E2E, tenant_id=_TENANT_AUDITOR)
        state = await planner.execute(state)
        assert state.current_agent == "auditor_planner"

        # Phase 2: 統制テスト
        mock_llm_gateway.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"test_results": [{"control_id": "AC-001",'
                ' "status": "effective", "score": 92},'
                ' {"control_id": "FP-001", "status": "partially_effective",'
                ' "score": 75}], "summary": "2件テスト完了"}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=400,
                output_tokens=200,
                total_tokens=600,
                cost_usd=0.004,
                latency_ms=1500.0,
            )
        )

        tester = ControlsTesterAgent(llm_gateway=mock_llm_gateway)
        state = await tester.execute(state)
        assert state.current_agent == "auditor_controls_tester"

        # Phase 3: レポート生成
        mock_llm_gateway.generate = AsyncMock(
            return_value=LLMResponse(
                content='{"report": {"title": "FY2025 Q4 Audit Report",'
                ' "findings": 1, "recommendations": 2,'
                ' "overall_rating": "satisfactory"},'
                ' "summary": "レポート生成完了"}',
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=500,
                output_tokens=300,
                total_tokens=800,
                cost_usd=0.005,
                latency_ms=2000.0,
            )
        )

        writer = ReportWriterAgent(llm_gateway=mock_llm_gateway)
        state = await writer.execute(state)
        assert state.current_agent == "auditor_report_writer"

    async def test_cross_tenant_dialogue_with_quality(self) -> None:
        """テナント間対話 + 品質評価テスト"""
        from uuid import uuid4

        from src.dialogue.bus import DialogueBus
        from src.dialogue.protocol import (
            AnswerMessage,
            ClarificationMessage,
            QuestionMessage,
        )
        from src.dialogue.quality import QualityEvaluator

        bus = DialogueBus(quality_evaluator=QualityEvaluator())

        auditor_tenant = uuid4()
        auditee_tenant = uuid4()

        # Step 1: 質問
        q = await bus.send(
            QuestionMessage(
                from_tenant_id=auditor_tenant,
                to_tenant_id=auditee_tenant,
                from_agent="auditor_controls_tester",
                content="売上計上プロセスにおける承認統制の詳細を教えてください。",
                priority="high",
            )
        )

        # Step 2: 明確化依頼
        clarify = await bus.send(
            ClarificationMessage(
                from_tenant_id=auditee_tenant,
                to_tenant_id=auditor_tenant,
                from_agent="auditee_response",
                content="具体的にどの承認段階についてお聞きになりたいですか？",
                thread_id=q.thread_id,
                parent_message_id=q.id,
            )
        )

        # Step 3: 追加質問
        q2 = await bus.send(
            QuestionMessage(
                from_tenant_id=auditor_tenant,
                to_tenant_id=auditee_tenant,
                from_agent="auditor_controls_tester",
                content="1次承認（部長承認）から最終承認（CFO承認）までの全段階を教えてください。",
                priority="medium",
                thread_id=q.thread_id,
                parent_message_id=clarify.id,
            )
        )

        # Step 4: 回答
        await bus.send(
            AnswerMessage(
                from_tenant_id=auditee_tenant,
                to_tenant_id=auditor_tenant,
                from_agent="auditee_response",
                content=(
                    "売上計上プロセスの承認統制は3段階制です：\n"
                    "1. 担当者入力（営業部）\n"
                    "2. 部長承認（1,000万円以上）\n"
                    "3. CFO承認（5,000万円以上）\n"
                    "全承認はSAPワークフローで電子的に管理されています。"
                ),
                confidence=0.92,
                thread_id=q.thread_id,
                parent_message_id=q2.id,
            )
        )

        # 検証
        thread = bus.get_thread(q.thread_id)
        assert len(thread) == 4
        assert thread[0].message_type.value == "question"
        assert thread[1].message_type.value == "clarification"
        assert thread[2].message_type.value == "question"
        assert thread[3].message_type.value == "answer"

    async def test_dialogue_escalation_flow(self) -> None:
        """エスカレーションフローテスト"""
        from uuid import uuid4

        from src.dialogue.bus import DialogueBus
        from src.dialogue.protocol import EscalationMessage, QuestionMessage

        bus = DialogueBus()
        auditor_tenant = uuid4()
        auditee_tenant = uuid4()

        # 質問
        q = await bus.send(
            QuestionMessage(
                from_tenant_id=auditor_tenant,
                to_tenant_id=auditee_tenant,
                from_agent="auditor_controls_tester",
                content="購買承認が無効化されているケースがあります。",
                priority="high",
            )
        )

        # エスカレーション
        await bus.send(
            EscalationMessage(
                from_tenant_id=auditor_tenant,
                to_tenant_id=auditee_tenant,
                from_agent="auditor_orchestrator",
                content="重大な統制不備の可能性があり、マネジメントへのエスカレーションが必要です。",
                severity="critical",
                thread_id=q.thread_id,
                parent_message_id=q.id,
            )
        )

        thread = bus.get_thread(q.thread_id)
        assert len(thread) == 2
        assert thread[1].message_type.value == "escalation"


@pytest.mark.e2e
class TestSelfAssessmentE2E:
    """セルフアセスメントE2Eテスト"""

    def test_assessment_config_creation(self) -> None:
        """設定作成テスト"""
        pytest.importorskip("temporalio")
        from src.workflows.self_assessment import AssessmentConfig

        config = AssessmentConfig(
            fiscal_year=2026,
            quarter=1,
            departments=["finance", "it"],
        )
        assert config.fiscal_year == 2026
        assert len(config.departments) == 2

    def test_workflow_state_management(self) -> None:
        """ワークフローステート管理テスト"""
        pytest.importorskip("temporalio")
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        wf._state = {
            "tenant_id": "tenant-e2e",
            "current_phase": "evaluation",
            "departments": ["finance", "purchasing"],
            "department_results": {
                "finance": {"status": "completed", "score": 88.0},
                "purchasing": {"status": "completed", "score": 76.0},
            },
            "overall_score": 82.0,
        }

        progress = wf.get_progress()
        assert progress["current_phase"] == "evaluation"
        assert progress["departments_completed"] == 2
        assert progress["departments_total"] == 2
        assert progress["overall_score"] == 82.0

    async def test_workflow_signal_handling(self) -> None:
        """シグナルハンドリングテスト"""
        pytest.importorskip("temporalio")
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()

        # 承認
        assert wf._approved is False
        await wf.approve()
        assert wf._approved is True

        # 却下（別インスタンス）
        wf2 = SelfAssessmentWorkflow()
        await wf2.reject("品質基準未達")
        assert wf2._rejection_reason == "品質基準未達"
