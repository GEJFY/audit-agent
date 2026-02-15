"""Dialogue Protocol テスト"""

from uuid import uuid4

import pytest

from src.config.constants import DialogueMessageType
from src.dialogue.protocol import (
    AnswerMessage,
    DialogueMessageSchema,
    EscalationMessage,
    EvidenceRequestMessage,
    QuestionMessage,
)


@pytest.mark.unit
class TestDialogueProtocol:
    """対話プロトコルのユニットテスト"""

    def test_create_question_message(self) -> None:
        """質問メッセージ作成テスト"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_controls_tester",
            content="購買承認フローの詳細を教えてください",
            priority="high",
        )

        assert msg.message_type == DialogueMessageType.QUESTION
        assert msg.priority == "high"
        assert msg.human_approved is None

    def test_create_answer_message(self) -> None:
        """回答メッセージ作成テスト"""
        msg = AnswerMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_response",
            content="購買承認フローは3段階制です。",
            confidence=0.85,
            is_reused=False,
        )

        assert msg.message_type == DialogueMessageType.ANSWER
        assert msg.confidence == 0.85

    def test_create_evidence_request(self) -> None:
        """証跡依頼メッセージ作成テスト"""
        msg = EvidenceRequestMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_data_collector",
            content="Q3の承認記録を提出してください",
            evidence_description="Q3承認記録",
            accepted_formats=["pdf", "xlsx"],
        )

        assert msg.message_type == DialogueMessageType.EVIDENCE_REQUEST
        assert "pdf" in msg.accepted_formats

    def test_create_escalation_message(self) -> None:
        """エスカレーションメッセージ作成テスト"""
        msg = EscalationMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditee_risk_alert",
            content="重大リスク検出",
            urgency="high",
        )

        assert msg.message_type == DialogueMessageType.ESCALATION
        assert msg.is_escalated is True

    def test_message_validation_same_tenant(self) -> None:
        """同一テナントへの送信はDialogueBusで検証"""
        # Protocol自体はバリデーションしない
        tenant_id = uuid4()
        msg = DialogueMessageSchema(
            from_tenant_id=tenant_id,
            to_tenant_id=tenant_id,  # 同一テナント
            from_agent="test",
            message_type=DialogueMessageType.QUESTION,
            content="test",
        )
        # Pydanticレベルでは作成可能（Bus側で検証）
        assert msg.from_tenant_id == msg.to_tenant_id
