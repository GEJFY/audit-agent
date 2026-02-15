"""Dialogue DBモデル テスト"""

import pytest

from src.db.models.dialogue import DialogueMessage


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestDialogueMessage:
    def test_tablename(self) -> None:
        assert DialogueMessage.__tablename__ == "dialogue_messages"

    def test_has_required_columns(self) -> None:
        for col in [
            "from_tenant_id",
            "to_tenant_id",
            "from_agent",
            "message_type",
            "content",
        ]:
            assert _has_column(DialogueMessage, col), f"Missing column: {col}"

    def test_has_thread_columns(self) -> None:
        assert _has_column(DialogueMessage, "parent_message_id")
        assert _has_column(DialogueMessage, "thread_id")

    def test_has_approval_columns(self) -> None:
        assert _has_column(DialogueMessage, "human_approved")
        assert _has_column(DialogueMessage, "approved_by")
        assert _has_column(DialogueMessage, "approved_at")

    def test_has_escalation_columns(self) -> None:
        assert _has_column(DialogueMessage, "is_escalated")
        assert _has_column(DialogueMessage, "escalation_reason")

    def test_default_is_escalated(self) -> None:
        assert DialogueMessage.__table__.columns["is_escalated"].default.arg is False

    def test_has_timestamps(self) -> None:
        assert _has_column(DialogueMessage, "created_at")
        assert _has_column(DialogueMessage, "updated_at")

    def test_no_tenant_id_column(self) -> None:
        """DialogueMessageはTenantBaseModelではない（両テナント共有）"""
        assert not _has_column(DialogueMessage, "tenant_id")

    def test_has_from_to_tenant_indexed(self) -> None:
        from_col = DialogueMessage.__table__.columns["from_tenant_id"]
        to_col = DialogueMessage.__table__.columns["to_tenant_id"]
        assert from_col.index is True
        assert to_col.index is True
