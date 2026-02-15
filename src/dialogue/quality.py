"""回答品質自動評価エンジン — 多次元スコアリング"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from loguru import logger
from pydantic import BaseModel, Field

from src.dialogue.protocol import DialogueMessageSchema


# ── 品質評価結果 ──────────────────────────────────────────
class QualityBreakdown(BaseModel):
    """品質スコアの内訳"""

    completeness: float = 0.0
    evidence_sufficiency: float = 0.0
    content_depth: float = 0.0
    timeliness: float = 0.0
    overall: float = 0.0


class QualityResult(BaseModel):
    """品質評価結果"""

    score: float = 0.0
    breakdown: QualityBreakdown = Field(default_factory=QualityBreakdown)
    issues: list[str] = Field(default_factory=list)


# ── 評価ウェイト設定 ──────────────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "completeness": 0.35,
    "evidence_sufficiency": 0.25,
    "content_depth": 0.25,
    "timeliness": 0.15,
}


class QualityEvaluator:
    """回答品質を自動評価（多次元スコアリング）

    評価基準:
    - 完全性 (35%): 質問の全ポイントに回答しているか
    - 証跡十分性 (25%): 適切な証跡が添付されているか
    - 内容深度 (25%): 回答の詳細度・構造化度
    - 適時性 (15%): 期限内に回答されているか
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._weights = weights or DEFAULT_WEIGHTS

    async def evaluate(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> float:
        """回答品質スコアを算出 (0.0-1.0)

        後方互換性のため float を返す。
        詳細が必要な場合は evaluate_detailed を使用。
        """
        result = await self.evaluate_detailed(answer, thread)
        return result.score

    async def evaluate_detailed(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> QualityResult:
        """多次元品質評価を実行し、内訳付き結果を返す"""
        issues: list[str] = []

        # 各軸のスコアを算出
        completeness = self._check_completeness(answer, thread)
        evidence = self._check_evidence(answer)
        depth = self._check_content_depth(answer, thread)
        timeliness = self._check_timeliness(answer, thread)

        # 問題点を検出
        if completeness < 0.5:
            issues.append("回答が質問のポイントを十分にカバーしていません")
        if evidence < 0.5:
            issues.append("証跡の添付が不足しています")
        if depth < 0.5:
            issues.append("回答の内容が浅い、または短すぎます")
        if timeliness < 0.5:
            issues.append("回答が期限を超過しています")

        # 重み付き加重平均
        overall = (
            completeness * self._weights["completeness"]
            + evidence * self._weights["evidence_sufficiency"]
            + depth * self._weights["content_depth"]
            + timeliness * self._weights["timeliness"]
        )
        overall = round(overall, 2)

        breakdown = QualityBreakdown(
            completeness=round(completeness, 2),
            evidence_sufficiency=round(evidence, 2),
            content_depth=round(depth, 2),
            timeliness=round(timeliness, 2),
            overall=overall,
        )

        logger.debug(
            "品質評価",
            message_id=str(answer.id),
            completeness=breakdown.completeness,
            evidence=breakdown.evidence_sufficiency,
            depth=breakdown.content_depth,
            timeliness=breakdown.timeliness,
            overall=overall,
        )

        return QualityResult(
            score=overall,
            breakdown=breakdown,
            issues=issues,
        )

    # ── 完全性チェック ──────────────────────────────────
    def _check_completeness(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> float:
        """完全性チェック — 質問のポイントに回答しているか

        1. 質問中の疑問文（「？」「か」等）の数 → カバー率
        2. 回答の長さと質問の複雑さの比率
        """
        questions = [m for m in thread if m.message_type.value == "question"]
        if not questions:
            return 0.5

        question_text = " ".join(q.content for q in questions)
        answer_text = answer.content

        if not question_text:
            return 0.5

        # 質問ポイント数を推定（疑問文カウント）
        question_points = _count_question_points(question_text)
        question_points = max(question_points, 1)

        # 回答中の段落 / 文の数を推定
        answer_sentences = _count_sentences(answer_text)

        # カバー率（回答文数 / 質問ポイント数）
        coverage = min(1.0, answer_sentences / question_points)

        # 長さ比率（従来ロジック）
        ratio = min(1.0, (len(answer_text) / len(question_text)) * 0.5)

        # 2つの指標の平均
        return (coverage * 0.6) + (ratio * 0.4)

    # ── 証跡チェック ────────────────────────────────────
    def _check_evidence(self, answer: DialogueMessageSchema) -> float:
        """証跡添付チェック"""
        if answer.attachments:
            # 添付数に応じてボーナス（最大1.0）
            return min(1.0, 0.7 + len(answer.attachments) * 0.1)

        if answer.structured_content.get("evidence_to_attach"):
            return 0.7

        # referenced_documents がある場合（AnswerMessage）
        refs = answer.structured_content.get("referenced_documents", [])
        if refs:
            return min(1.0, 0.5 + len(refs) * 0.1)

        return 0.3

    # ── 内容深度チェック ────────────────────────────────
    def _check_content_depth(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> float:
        """回答の内容深度を評価

        - 文字数（基本スコア）
        - 構造化度（箇条書き、番号付きリスト等）
        - 具体性（数値、日付、固有名詞の含有）
        """
        text = answer.content
        score = 0.0

        # 基本スコア: 文字数（100文字で0.5, 300文字で1.0）
        length_score = min(1.0, len(text) / 300)
        score += length_score * 0.4

        # 構造化スコア: 箇条書き/番号付きリスト
        structure_score = _check_structure(text)
        score += structure_score * 0.3

        # 具体性スコア: 数値・日付・固有名詞の含有
        specificity_score = _check_specificity(text)
        score += specificity_score * 0.3

        return min(1.0, score)

    # ── 適時性チェック ──────────────────────────────────
    def _check_timeliness(
        self,
        answer: DialogueMessageSchema,
        thread: list[DialogueMessageSchema],
    ) -> float:
        """期限内回答か評価

        QuestionMessage に deadline がある場合、それと回答時刻を比較。
        deadline がない場合は1.0（ペナルティなし）。
        """
        # スレッドから直近の質問を取得
        questions = [m for m in thread if m.message_type.value == "question"]
        if not questions:
            return 1.0

        latest_question = questions[-1]

        # deadline を取得（QuestionMessage のフィールド）
        deadline = getattr(latest_question, "deadline", None)
        if deadline is None:
            # structured_content からも試行
            deadline_str = latest_question.structured_content.get("deadline")
            if deadline_str and isinstance(deadline_str, str):
                try:
                    deadline = datetime.fromisoformat(deadline_str)
                except ValueError:
                    return 1.0
            else:
                return 1.0

        # 回答時刻と比較
        answer_time = answer.timestamp
        if not answer_time.tzinfo:
            answer_time = answer_time.replace(tzinfo=UTC)
        if not deadline.tzinfo:
            deadline = deadline.replace(tzinfo=UTC)

        if answer_time <= deadline:
            return 1.0

        # 超過時間に応じてスコアを減衰
        overdue_hours = (answer_time - deadline).total_seconds() / 3600
        if overdue_hours <= 1:
            return 0.8
        if overdue_hours <= 24:
            return 0.5
        return 0.2


# ── ヘルパー関数 ──────────────────────────────────────────


def _count_question_points(text: str) -> int:
    """テキスト中の質問ポイント数を推定"""
    # 疑問符（全角・半角）をカウント
    question_marks = len(re.findall(r"[？?]", text))
    # 箇条書きの質問
    list_items = len(re.findall(r"^[\s]*[-・●▪]\s", text, re.MULTILINE))

    return max(1, question_marks + list_items)


def _count_sentences(text: str) -> int:
    """テキスト中の文の数を推定"""
    # 日本語文末（。）+ 英語文末（.!?）
    endings = len(re.findall(r"[。.!?！？]", text))
    # 改行区切りの段落もカウント
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return max(endings, len(lines))


def _check_structure(text: str) -> float:
    """テキストの構造化度をチェック"""
    score = 0.0

    # 箇条書き
    bullet_count = len(re.findall(r"^[\s]*[-・●▪★]\s", text, re.MULTILINE))
    if bullet_count >= 3:
        score += 0.5
    elif bullet_count >= 1:
        score += 0.3

    # 番号付きリスト
    numbered_count = len(re.findall(r"^[\s]*\d+[.)．]\s", text, re.MULTILINE))
    if numbered_count >= 2:
        score += 0.3

    # 見出し的な構造（「■」「【】」等）
    heading_count = len(re.findall(r"[■□▼▽【】]|^#+\s", text, re.MULTILINE))
    if heading_count >= 1:
        score += 0.2

    return min(1.0, score)


def _check_specificity(text: str) -> float:
    """テキストの具体性をチェック"""
    score = 0.0

    # 数値の含有
    numbers = re.findall(r"\d+(?:[.,]\d+)?(?:%|円|件|回|個|名)?", text)
    if len(numbers) >= 3:
        score += 0.4
    elif len(numbers) >= 1:
        score += 0.2

    # 日付の含有
    dates = re.findall(
        r"\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}月\d{1,2}日|\d{4}年",
        text,
    )
    if dates:
        score += 0.3

    # 固有名詞的パターン（部門名、システム名等）
    proper_nouns = re.findall(r"「[^」]+」|『[^』]+』", text)
    if proper_nouns:
        score += 0.3

    return min(1.0, score)
