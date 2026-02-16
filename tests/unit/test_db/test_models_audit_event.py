"""監査イベントDBモデル テスト"""

import pytest

from src.db.models.audit_event import AuditEvent


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestAuditEvent:
    def test_tablename(self) -> None:
        assert AuditEvent.__tablename__ == "audit_events"

    def test_has_required_columns(self) -> None:
        for col in [
            "id",
            "tenant_id",
            "event_type",
            "resource_type",
            "actor_type",
        ]:
            assert _has_column(AuditEvent, col), f"Missing column: {col}"

    def test_has_optional_columns(self) -> None:
        for col in [
            "resource_id",
            "actor_id",
            "description",
            "ip_address",
            "user_agent",
            "before_state",
            "after_state",
            "project_id",
        ]:
            assert _has_column(AuditEvent, col), f"Missing column: {col}"

    def test_default_actor_type(self) -> None:
        col = AuditEvent.__table__.columns["actor_type"]
        assert col.default.arg == "user"

    def test_has_timestamps(self) -> None:
        assert _has_column(AuditEvent, "created_at")
        assert _has_column(AuditEvent, "updated_at")

    def test_event_type_indexed(self) -> None:
        col = AuditEvent.__table__.columns["event_type"]
        assert col.index is True

    def test_actor_id_indexed(self) -> None:
        col = AuditEvent.__table__.columns["actor_id"]
        assert col.index is True

    def test_project_id_indexed(self) -> None:
        col = AuditEvent.__table__.columns["project_id"]
        assert col.index is True

    def test_nullable_fields(self) -> None:
        """NULLを許容すべきフィールドの確認"""
        nullable_cols = [
            "resource_id",
            "actor_id",
            "description",
            "ip_address",
            "user_agent",
            "before_state",
            "after_state",
            "project_id",
        ]
        for col_name in nullable_cols:
            col = AuditEvent.__table__.columns[col_name]
            assert col.nullable is True, f"{col_name} should be nullable"

    def test_non_nullable_fields(self) -> None:
        """NOT NULLフィールドの確認"""
        for col_name in ["event_type", "resource_type"]:
            col = AuditEvent.__table__.columns[col_name]
            assert col.nullable is False, f"{col_name} should be NOT NULL"
