"""Dialogue Bus テスト"""

import pytest
from uuid import uuid4

from src.config.constants import DialogueMessageType
from src.dialogue.bus import DialogueBus
from src.dialogue.protocol import QuestionMessage, AnswerMessage


@pytest.fixture
def dialogue_bus() -> DialogueBus:
    return DialogueBus()


@pytest.mark.unit
class TestDialogueBus:
    """Dialogue Busのユニットテスト"""

    async def test_send_message(self, dialogue_bus: DialogueBus) -> None:
        """メッセージ送信テスト"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_controls_tester",
            content="テスト質問",
        )

        result = await dialogue_bus.send(msg)

        assert result.id == msg.id
        assert result.thread_id is not None

    async def test_thread_management(self, dialogue_bus: DialogueBus) -> None:
        """スレッド管理テスト"""
        auditor_id = uuid4()
        auditee_id = uuid4()

        # 質問送信
        q = QuestionMessage(
            from_tenant_id=auditor_id,
            to_tenant_id=auditee_id,
            from_agent="auditor_controls_tester",
            content="質問です",
        )
        sent_q = await dialogue_bus.send(q)

        # 回答送信（同じスレッド）
        a = AnswerMessage(
            from_tenant_id=auditee_id,
            to_tenant_id=auditor_id,
            from_agent="auditee_response",
            content="回答です",
            thread_id=sent_q.thread_id,
            parent_message_id=sent_q.id,
        )
        await dialogue_bus.send(a)

        # スレッド取得
        thread = dialogue_bus.get_thread(sent_q.thread_id)
        assert len(thread) == 2

    async def test_validation_same_tenant(self, dialogue_bus: DialogueBus) -> None:
        """同一テナント送信の検証"""
        tenant_id = uuid4()
        msg = QuestionMessage(
            from_tenant_id=tenant_id,
            to_tenant_id=tenant_id,
            from_agent="test",
            content="test",
        )

        with pytest.raises(ValueError, match="同一テナント"):
            await dialogue_bus.send(msg)

    async def test_validation_empty_content(self, dialogue_bus: DialogueBus) -> None:
        """空メッセージの検証"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="",
        )

        with pytest.raises(ValueError, match="空"):
            await dialogue_bus.send(msg)

    async def test_approve_message(self, dialogue_bus: DialogueBus) -> None:
        """メッセージ承認テスト"""
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="承認テスト",
        )
        sent = await dialogue_bus.send(msg)
        approver_id = uuid4()

        result = dialogue_bus.approve_message(sent.id, approver_id)

        assert result is True

    async def test_get_pending_approvals(self, dialogue_bus: DialogueBus) -> None:
        """承認待ちメッセージ取得テスト"""
        tenant_id = uuid4()
        msg = QuestionMessage(
            from_tenant_id=tenant_id,
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )
        await dialogue_bus.send(msg)

        pending = dialogue_bus.get_pending_approvals(tenant_id)
        assert len(pending) == 1
