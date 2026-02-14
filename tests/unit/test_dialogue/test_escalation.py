"""Escalation Engine テスト"""

from uuid import uuid4

import pytest

from src.config.constants import DialogueMessageType, EscalationReason
from src.dialogue.escalation import EscalationEngine
from src.dialogue.protocol import DialogueMessageSchema


@pytest.fixture
def engine() -> EscalationEngine:
    return EscalationEngine()


@pytest.mark.unit
class TestEscalationEngine:
    """エスカレーションエンジンのユニットテスト"""

    def test_should_escalate_low_confidence(self, engine: EscalationEngine) -> None:
        """低信頼度でエスカレーション"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_response",
            message_type=DialogueMessageType.ANSWER,
            content="テスト回答",
            confidence=0.5,  # 閾値以下
        )

        assert engine.should_escalate(msg) is True

    def test_should_not_escalate_high_confidence(self, engine: EscalationEngine) -> None:
        """高信頼度ではエスカレーションしない"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_response",
            message_type=DialogueMessageType.ANSWER,
            content="テスト回答",
            confidence=0.9,
        )

        assert engine.should_escalate(msg) is False

    def test_should_not_escalate_already_escalated(self, engine: EscalationEngine) -> None:
        """既にエスカレーション済みのメッセージ"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_response",
            message_type=DialogueMessageType.ANSWER,
            content="テスト回答",
            confidence=0.3,
            is_escalated=True,
        )

        assert engine.should_escalate(msg) is False

    def test_should_escalate_with_reason(self, engine: EscalationEngine) -> None:
        """明示的なエスカレーション理由あり"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ESCALATION,
            content="重大リスク",
            escalation_reason=EscalationReason.HIGH_RISK_DETECTED,
        )

        assert engine.should_escalate(msg) is True

    def test_get_reason_low_confidence(self, engine: EscalationEngine) -> None:
        """低信頼度のエスカレーション理由"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
            confidence=0.5,
        )

        reason = engine.get_reason(msg)
        assert reason == EscalationReason.LOW_CONFIDENCE

    def test_get_reason_explicit(self, engine: EscalationEngine) -> None:
        """明示的エスカレーション理由"""
        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ESCALATION,
            content="ポリシー違反",
            escalation_reason=EscalationReason.POLICY_VIOLATION,
        )

        reason = engine.get_reason(msg)
        assert reason == EscalationReason.POLICY_VIOLATION

    def test_custom_threshold(self) -> None:
        """カスタム閾値でのエスカレーション判定"""
        strict_engine = EscalationEngine(confidence_threshold=0.9)

        msg = DialogueMessageSchema(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            message_type=DialogueMessageType.ANSWER,
            content="回答",
            confidence=0.85,
        )

        assert strict_engine.should_escalate(msg) is True
