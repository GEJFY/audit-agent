"""Quality Evaluator テスト"""

import pytest
from uuid import uuid4

from src.config.constants import DialogueMessageType
from src.dialogue.protocol import DialogueMessageSchema, QuestionMessage, AnswerMessage
from src.dialogue.quality import QualityEvaluator


@pytest.fixture
def evaluator() -> QualityEvaluator:
    return QualityEvaluator()


@pytest.mark.unit
class TestQualityEvaluator:
    """回答品質評価のユニットテスト"""

    async def test_evaluate_good_answer(self, evaluator: QualityEvaluator) -> None:
        """高品質回答の評価"""
        from_id = uuid4()
        to_id = uuid4()

        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor_controls_tester",
            content="購買承認フローの詳細を教えてください",
        )

        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="購買承認フローは以下の3段階で構成されています。第1段階は部門長承認、第2段階は経理部確認、第3段階は役員承認です。",
            confidence=0.9,
        )

        score = await evaluator.evaluate(answer, [question])

        assert 0.0 <= score <= 1.0
        assert score >= 0.3  # 最低限のスコア

    async def test_evaluate_short_answer(self, evaluator: QualityEvaluator) -> None:
        """極端に短い回答の評価"""
        from_id = uuid4()
        to_id = uuid4()

        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor",
            content="詳細な購買承認プロセスについて説明してください。また、関連する規定も提示してください。",
        )

        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="はい",
            confidence=0.5,
        )

        score = await evaluator.evaluate(answer, [question])

        assert score < 0.5  # 短すぎる回答は低スコア

    async def test_evaluate_no_thread(self, evaluator: QualityEvaluator) -> None:
        """スレッドなしの評価"""
        answer = AnswerMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_response",
            content="テスト回答です。十分な内容を含む回答。" * 5,
            confidence=0.8,
        )

        score = await evaluator.evaluate(answer, [])

        assert 0.0 <= score <= 1.0

    def test_check_evidence_with_attachments(self, evaluator: QualityEvaluator) -> None:
        """証跡付き回答のチェック"""
        from src.dialogue.protocol import Attachment

        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
            attachments=[
                Attachment(file_name="file1.pdf", file_type="pdf", s3_path="s3://bucket/file1.pdf")
            ],
        )

        score = evaluator._check_evidence(msg)
        assert score == 1.0

    def test_check_evidence_without_attachments(self, evaluator: QualityEvaluator) -> None:
        """証跡なし回答のチェック"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
        )

        score = evaluator._check_evidence(msg)
        assert score == 0.3  # 証跡なしは低スコア
