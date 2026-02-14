"""回答品質自動評価エンジン"""

from typing import Any

from loguru import logger

from src.dialogue.protocol import DialogueMessageSchema


class QualityEvaluator:
    """回答品質を自動評価

    評価基準:
    - 完全性: 質問の全ポイントに回答しているか
    - 正確性: 事実に基づいているか
    - 証跡十分性: 適切な証跡が添付されているか
    - 適時性: 期限内に回答されているか
    """

    async def evaluate(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> float:
        """回答品質スコアを算出 (0.0-1.0)"""
        scores: list[float] = []

        # 完全性チェック
        completeness = self._check_completeness(answer, thread)
        scores.append(completeness)

        # 証跡チェック
        evidence_score = self._check_evidence(answer)
        scores.append(evidence_score)

        # 内容の長さチェック（極端に短い回答はペナルティ）
        content_score = min(1.0, len(answer.content) / 100)
        scores.append(content_score)

        overall = sum(scores) / len(scores) if scores else 0.0

        logger.debug(
            "品質評価",
            message_id=str(answer.id),
            completeness=completeness,
            evidence=evidence_score,
            content=content_score,
            overall=round(overall, 2),
        )

        return round(overall, 2)

    def _check_completeness(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> float:
        """完全性チェック — 質問のポイントに回答しているか"""
        # 元の質問を取得
        questions = [m for m in thread if m.message_type.value == "question"]
        if not questions:
            return 0.5

        # 簡易チェック: 回答の長さと質問の複雑さの比率
        question_length = sum(len(q.content) for q in questions)
        answer_length = len(answer.content)

        if question_length == 0:
            return 0.5

        ratio = answer_length / question_length
        return min(1.0, ratio * 0.5)

    def _check_evidence(self, answer: DialogueMessageSchema) -> float:
        """証跡添付チェック"""
        if answer.attachments:
            return 1.0
        if answer.structured_content.get("evidence_to_attach"):
            return 0.7
        return 0.3
