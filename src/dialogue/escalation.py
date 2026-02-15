"""エスカレーションエンジン — 自動エスカレーション判定"""

from loguru import logger

from src.config.constants import CONFIDENCE_THRESHOLD, EscalationReason
from src.dialogue.protocol import DialogueMessageSchema
from src.monitoring.metrics import escalations_total


class EscalationEngine:
    """エスカレーション判定エンジン

    判定条件:
    1. 信頼度スコア < 閾値
    2. 回答期限超過
    3. 重大リスク検出
    4. 人間レビュー必須の判断
    5. ポリシー違反検知
    """

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD) -> None:
        self._confidence_threshold = confidence_threshold

    def should_escalate(self, message: DialogueMessageSchema) -> bool:
        """エスカレーションが必要か判定"""
        # 既にエスカレーション済み
        if message.is_escalated:
            return False

        # 信頼度チェック
        if message.confidence is not None and message.confidence < self._confidence_threshold:
            return True

        # エスカレーション理由が設定されている場合
        return message.escalation_reason is not None

    def get_reason(self, message: DialogueMessageSchema) -> EscalationReason:
        """エスカレーション理由を判定"""
        if message.escalation_reason:
            reason = message.escalation_reason
        elif message.confidence is not None and message.confidence < self._confidence_threshold:
            reason = EscalationReason.LOW_CONFIDENCE
        else:
            reason = EscalationReason.HUMAN_REVIEW_REQUIRED

        # メトリクス記録
        severity = "high" if message.confidence and message.confidence < 0.5 else "medium"
        escalations_total.labels(reason=reason.value, severity=severity).inc()

        logger.info(
            "エスカレーション判定",
            reason=reason.value,
            message_id=str(message.id),
            confidence=message.confidence,
        )

        return reason
