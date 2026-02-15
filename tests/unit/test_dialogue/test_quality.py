"""Quality Evaluator テスト — 多次元スコアリング"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.config.constants import DialogueMessageType
from src.dialogue.protocol import AnswerMessage, Attachment, DialogueMessageSchema, QuestionMessage
from src.dialogue.quality import (
    QualityEvaluator,
    QualityResult,
    _check_specificity,
    _check_structure,
    _count_question_points,
    _count_sentences,
)


@pytest.fixture
def evaluator() -> QualityEvaluator:
    return QualityEvaluator()


def _make_ids() -> tuple:
    return uuid4(), uuid4()


@pytest.mark.unit
class TestQualityEvaluator:
    """回答品質評価のユニットテスト"""

    async def test_evaluate_good_answer(self, evaluator: QualityEvaluator) -> None:
        """高品質回答の評価"""
        from_id, to_id = _make_ids()

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
        assert score >= 0.3

    async def test_evaluate_short_answer(self, evaluator: QualityEvaluator) -> None:
        """極端に短い回答の評価"""
        from_id, to_id = _make_ids()

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
        assert score < 0.5

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
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
            attachments=[
                Attachment(
                    file_name="file1.pdf",
                    file_type="pdf",
                    s3_path="s3://bucket/file1.pdf",
                    file_hash="abc123def456",
                )
            ],
        )

        score = evaluator._check_evidence(msg)
        assert score >= 0.7

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
        assert score == 0.3

    # ── 多次元評価テスト ──────────────────────────────

    async def test_evaluate_detailed_returns_breakdown(self, evaluator: QualityEvaluator) -> None:
        """evaluate_detailed が QualityResult と内訳を返す"""
        from_id, to_id = _make_ids()
        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor",
            content="内部統制の整備状況について詳細を教えてください。",
        )
        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="内部統制の整備状況は以下の通りです。"
            "1. 購買承認フロー: 3段階承認（部門長→経理→役員）"
            "2. アクセス管理: 四半期ごとの権限レビュー"
            "3. 変更管理: 「変更管理規程」に基づく承認プロセス",
        )

        result = await evaluator.evaluate_detailed(answer, [question])

        assert isinstance(result, QualityResult)
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.breakdown.completeness <= 1.0
        assert 0.0 <= result.breakdown.evidence_sufficiency <= 1.0
        assert 0.0 <= result.breakdown.content_depth <= 1.0
        assert 0.0 <= result.breakdown.timeliness <= 1.0
        assert result.breakdown.overall == result.score

    async def test_timeliness_on_time(self, evaluator: QualityEvaluator) -> None:
        """期限内回答は timeliness = 1.0"""
        from_id, to_id = _make_ids()
        now = datetime.now(UTC)

        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor",
            content="テスト質問です。",
            deadline=now + timedelta(hours=24),
        )

        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="期限内の回答です。十分な内容を含む回答テスト。",
            timestamp=now,
        )

        timeliness = evaluator._check_timeliness(answer, [question])
        assert timeliness == 1.0

    async def test_timeliness_overdue(self, evaluator: QualityEvaluator) -> None:
        """期限超過回答は timeliness < 1.0"""
        from_id, to_id = _make_ids()
        deadline = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)

        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor",
            content="テスト質問です。",
            deadline=deadline,
        )

        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="遅延した回答です。",
            timestamp=deadline + timedelta(hours=48),
        )

        timeliness = evaluator._check_timeliness(answer, [question])
        assert timeliness < 0.5

    async def test_timeliness_no_deadline(self, evaluator: QualityEvaluator) -> None:
        """deadline なしの場合は 1.0"""
        from_id, to_id = _make_ids()

        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor",
            content="テスト質問です。",
        )

        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="回答です。",
        )

        timeliness = evaluator._check_timeliness(answer, [question])
        assert timeliness == 1.0

    async def test_quality_issues_detected(self, evaluator: QualityEvaluator) -> None:
        """低品質回答で issues が検出される"""
        from_id, to_id = _make_ids()
        question = QuestionMessage(
            from_tenant_id=from_id,
            to_tenant_id=to_id,
            from_agent="auditor",
            content="詳細な購買承認プロセスの全手順と関連規程を説明してください。",
        )
        answer = AnswerMessage(
            from_tenant_id=to_id,
            to_tenant_id=from_id,
            from_agent="auditee_response",
            content="はい",
        )

        result = await evaluator.evaluate_detailed(answer, [question])
        assert len(result.issues) >= 1

    async def test_evidence_with_referenced_documents(self, evaluator: QualityEvaluator) -> None:
        """referenced_documents がある場合の証跡スコア"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
            structured_content={"referenced_documents": ["doc1.pdf", "doc2.xlsx", "doc3.csv"]},
        )

        score = evaluator._check_evidence(msg)
        assert score >= 0.5

    async def test_custom_weights(self) -> None:
        """カスタムウェイトでの評価"""
        custom_weights = {
            "completeness": 0.5,
            "evidence_sufficiency": 0.2,
            "content_depth": 0.2,
            "timeliness": 0.1,
        }
        evaluator = QualityEvaluator(weights=custom_weights)

        answer = AnswerMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_response",
            content="カスタムウェイトテスト。" * 10,
        )

        result = await evaluator.evaluate_detailed(answer, [])
        assert 0.0 <= result.score <= 1.0

    async def test_evidence_multiple_attachments_bonus(self, evaluator: QualityEvaluator) -> None:
        """複数添付でボーナススコア"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
            attachments=[
                Attachment(
                    file_name=f"file{i}.pdf",
                    file_type="pdf",
                    s3_path=f"s3://bucket/file{i}.pdf",
                    file_hash=f"hash{i}",
                )
                for i in range(4)
            ],
        )

        score = evaluator._check_evidence(msg)
        assert score == 1.0


@pytest.mark.unit
class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_count_question_points_ja(self) -> None:
        """日本語の質問ポイント数カウント"""
        text = "承認フローはどうなっていますか？また、権限管理の方法は？"
        count = _count_question_points(text)
        assert count >= 2

    def test_count_question_points_en(self) -> None:
        """英語の質問ポイント数カウント"""
        text = "What is the approval flow? How is access managed?"
        count = _count_question_points(text)
        assert count >= 2

    def test_count_sentences(self) -> None:
        """文の数カウント"""
        text = "第1文です。第2文です。第3文です。"
        count = _count_sentences(text)
        assert count >= 3

    def test_check_structure_with_bullets(self) -> None:
        """箇条書きの構造化スコア"""
        text = "以下の項目:\n- 項目1\n- 項目2\n- 項目3\n- 項目4"
        score = _check_structure(text)
        assert score >= 0.5

    def test_check_structure_with_numbers(self) -> None:
        """番号付きリストの構造化スコア"""
        text = "手順:\n1. 申請書の作成\n2. 部門長の承認\n3. 経理部の確認"
        score = _check_structure(text)
        assert score >= 0.3

    def test_check_structure_plain_text(self) -> None:
        """プレーンテキストの構造化スコア"""
        text = "これは構造化されていない回答です"
        score = _check_structure(text)
        assert score < 0.3

    def test_check_specificity_with_numbers(self) -> None:
        """数値を含むテキストの具体性"""
        text = "2024年度の取引件数は1,234件で、承認率は98.5%でした。金額は約5000万円です。"
        score = _check_specificity(text)
        assert score >= 0.4

    def test_check_specificity_with_dates(self) -> None:
        """日付を含むテキストの具体性"""
        text = "2024年4月1日に規程を改定しました。次回レビューは2024/10/01の予定です。"
        score = _check_specificity(text)
        assert score >= 0.3

    def test_check_specificity_with_proper_nouns(self) -> None:
        """固有名詞を含むテキストの具体性"""
        text = "「購買管理規程」に基づき、「SAP」システムで管理しています。"
        score = _check_specificity(text)
        assert score >= 0.3

    def test_check_specificity_vague_text(self) -> None:
        """曖昧なテキストの具体性"""
        text = "適切に管理しています"
        score = _check_specificity(text)
        assert score < 0.3
