"""通知DBモデル テスト"""

import pytest

from src.db.models.notification import Notification, NotificationSetting


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestNotification:
    def test_tablename(self) -> None:
        assert Notification.__tablename__ == "notifications"

    def test_has_required_columns(self) -> None:
        for col in [
            "id",
            "tenant_id",
            "title",
            "body",
            "priority",
            "source",
            "provider",
            "channel",
            "status",
        ]:
            assert _has_column(Notification, col), f"Missing column: {col}"

    def test_has_optional_columns(self) -> None:
        for col in [
            "action_url",
            "metadata",
            "project_id",
            "retry_count",
        ]:
            assert _has_column(Notification, col), f"Missing column: {col}"

    def test_default_priority(self) -> None:
        col = Notification.__table__.columns["priority"]
        assert col.default.arg == "medium"

    def test_default_status(self) -> None:
        col = Notification.__table__.columns["status"]
        assert col.default.arg == "sent"

    def test_default_retry_count(self) -> None:
        col = Notification.__table__.columns["retry_count"]
        assert col.default.arg == 0

    def test_has_timestamps(self) -> None:
        assert _has_column(Notification, "created_at")
        assert _has_column(Notification, "updated_at")

    def test_project_id_indexed(self) -> None:
        col = Notification.__table__.columns["project_id"]
        assert col.index is True


@pytest.mark.unit
class TestNotificationSetting:
    def test_tablename(self) -> None:
        assert NotificationSetting.__tablename__ == "notification_settings"

    def test_has_required_columns(self) -> None:
        for col in [
            "id",
            "tenant_id",
            "provider",
            "channel",
            "is_enabled",
            "min_priority",
        ]:
            assert _has_column(NotificationSetting, col), f"Missing column: {col}"

    def test_has_optional_columns(self) -> None:
        for col in ["webhook_url", "config"]:
            assert _has_column(NotificationSetting, col), f"Missing column: {col}"

    def test_default_enabled(self) -> None:
        col = NotificationSetting.__table__.columns["is_enabled"]
        assert col.default.arg is True

    def test_default_min_priority(self) -> None:
        col = NotificationSetting.__table__.columns["min_priority"]
        assert col.default.arg == "low"

    def test_has_timestamps(self) -> None:
        assert _has_column(NotificationSetting, "created_at")
        assert _has_column(NotificationSetting, "updated_at")
