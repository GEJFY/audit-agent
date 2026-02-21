"""品質評価統合テスト — DialogueBus + QualityEvaluator E2Eフロー"""

from uuid import uuid4

import pytest

from src.dialogue.bus import DialogueBus
from src.dialogue.protocol import AnswerMessage, QuestionMessage
from src.dialogue.quality import QualityEvaluator


@pytest.fixture
def bus() -> DialogueBus:
    return DialogueBus()


@pytest.mark.unit
class TestQualityIntegration:
    """DialogueBus の品質評価統合テスト"""

    async def test_answer_gets_quality_score(self, bus: DialogueBus) -> None:
        """回答メッセージに品質スコアが自動付与される"""
        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_controls_tester",
            content="内部統制の整備状況について説明してください？",
        )
        sent_q = await bus.send(q)

        a = AnswerMessage(
            from_tenant_id=auditee,
            to_tenant_id=auditor,
            from_agent="auditee_response",
            content="統制環境は経営者の姿勢に基づき整備されています。"
            "具体的には、2024年4月に内部統制委員会を設置し、"
            "月次レビューを実施しています。",
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        sent_a = await bus.send(a)

        assert sent_a.quality_score is not None
        assert 0.0 <= sent_a.quality_score <= 1.0

    async def test_quality_breakdown_in_metadata(self, bus: DialogueBus) -> None:
        """品質内訳がメタデータに保存される"""
        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="リスク評価プロセスの実施頻度は？",
        )
        sent_q = await bus.send(q)

        a = AnswerMessage(
            from_tenant_id=auditee,
            to_tenant_id=auditor,
            from_agent="auditee_response",
            content="四半期ごとに実施。直近は2024年3月に完了。",
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        sent_a = await bus.send(a)

        breakdown = sent_a.metadata.get("quality_breakdown")
        assert breakdown is not None
        assert "completeness" in breakdown
        assert "evidence_sufficiency" in breakdown
        assert "content_depth" in breakdown
        assert "timeliness" in breakdown
        assert "overall" in breakdown

    async def test_low_quality_generates_issues(self, bus: DialogueBus) -> None:
        """低品質回答には問題点リストが付与される"""
        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="監査計画のリスク評価手法は？リスク要因の洗い出し方法は？ステークホルダーとの合意プロセスは？",
        )
        sent_q = await bus.send(q)

        # 非常に短い回答（品質が低い）
        a = AnswerMessage(
            from_tenant_id=auditee,
            to_tenant_id=auditor,
            from_agent="auditee_response",
            content="はい",
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        sent_a = await bus.send(a)

        assert sent_a.quality_score is not None
        assert sent_a.quality_score < 0.5
        issues = sent_a.metadata.get("quality_issues", [])
        assert len(issues) > 0

    async def test_question_message_no_quality_score(self, bus: DialogueBus) -> None:
        """質問メッセージには品質スコアが付与されない"""
        q = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_planner",
            content="テスト質問",
        )
        sent = await bus.send(q)

        assert sent.quality_score is None

    async def test_custom_quality_evaluator(self) -> None:
        """カスタムウェイトのQualityEvaluatorが使用可能"""
        evaluator = QualityEvaluator(
            weights={
                "completeness": 0.5,
                "evidence_sufficiency": 0.2,
                "content_depth": 0.2,
                "timeliness": 0.1,
            }
        )
        bus = DialogueBus(quality_evaluator=evaluator)

        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="テスト？",
        )
        sent_q = await bus.send(q)

        a = AnswerMessage(
            from_tenant_id=auditee,
            to_tenant_id=auditor,
            from_agent="auditee_response",
            content="回答内容です。",
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        sent_a = await bus.send(a)

        assert sent_a.quality_score is not None


@pytest.mark.unit
class TestHumanOverrideFlow:
    """Human Override（人的介入）フローテスト"""

    async def test_full_override_flow(self, bus: DialogueBus) -> None:
        """完全な承認フロー: 質問→回答→承認→確認"""
        auditor = uuid4()
        auditee = uuid4()
        approver = uuid4()

        # 1. 質問送信
        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_controls_tester",
            content="承認が必要な質問です",
        )
        sent_q = await bus.send(q)

        # 2. 承認待ち確認
        pending = bus.get_pending_approvals(auditor)
        assert len(pending) == 1
        assert pending[0].human_approved is None

        # 3. 承認実行
        result = bus.approve_message(sent_q.id, approver)
        assert result is True

        # 4. 承認後確認
        pending_after = bus.get_pending_approvals(auditor)
        assert len(pending_after) == 0

        # 5. メッセージの承認状態確認
        thread = bus.get_thread(sent_q.thread_id)
        approved_msg = thread[0]
        assert approved_msg.human_approved is True
        assert approved_msg.approved_by == approver
        assert approved_msg.approved_at is not None

    async def test_approve_nonexistent_message(self, bus: DialogueBus) -> None:
        """存在しないメッセージの承認は失敗する"""
        result = bus.approve_message(uuid4(), uuid4())
        assert result is False

    async def test_multiple_messages_approval(self, bus: DialogueBus) -> None:
        """複数メッセージの選択的承認"""
        auditor = uuid4()
        auditee = uuid4()
        approver = uuid4()

        # 2つの質問を送信
        q1 = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="質問1",
        )
        q2 = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="質問2",
        )
        sent_q1 = await bus.send(q1)
        sent_q2 = await bus.send(q2)

        # q1のみ承認
        bus.approve_message(sent_q1.id, approver)

        # q2はまだ承認待ち
        pending = bus.get_pending_approvals(auditor)
        assert len(pending) == 1
        assert pending[0].id == sent_q2.id

    async def test_tenant_message_filtering(self, bus: DialogueBus) -> None:
        """テナント別メッセージフィルタリング"""
        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="テナントフィルタテスト",
        )
        await bus.send(q)

        # 送信元テナントで取得
        messages = bus.get_messages_for_tenant(auditor)
        assert len(messages) == 1

        # 宛先テナントで取得
        messages = bus.get_messages_for_tenant(auditee)
        assert len(messages) == 1

        # 無関係テナント
        messages = bus.get_messages_for_tenant(uuid4())
        assert len(messages) == 0


@pytest.mark.unit
class TestEscalationIntegration:
    """エスカレーション統合テスト"""

    async def test_low_confidence_triggers_escalation(self, bus: DialogueBus) -> None:
        """低信頼度メッセージがエスカレーションをトリガー"""
        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="低信頼度テスト",
            confidence=0.3,
        )
        await bus.send(q)

        # エスカレーションメッセージが追加されている
        messages = bus.get_messages_for_tenant(auditor)
        escalation_msgs = [m for m in messages if "エスカレーション" in m.content]
        assert len(escalation_msgs) >= 1

    async def test_high_confidence_no_escalation(self, bus: DialogueBus) -> None:
        """高信頼度メッセージはエスカレーションされない"""
        auditor = uuid4()
        auditee = uuid4()

        q = QuestionMessage(
            from_tenant_id=auditor,
            to_tenant_id=auditee,
            from_agent="auditor_planner",
            content="高信頼度テスト",
            confidence=0.95,
        )
        await bus.send(q)

        # 元のメッセージのみ
        messages = bus.get_messages_for_tenant(auditor)
        assert len(messages) == 1
