"""NotificationRepository テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.notification import Notification, NotificationSetting
from src.db.repositories.notification import (
    NotificationRepository,
    NotificationSettingRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def notif_repo(mock_session: AsyncMock) -> NotificationRepository:
    return NotificationRepository(session=mock_session)


@pytest.fixture
def setting_repo(mock_session: AsyncMock) -> NotificationSettingRepository:
    return NotificationSettingRepository(session=mock_session)


def _mock_scalars(items: list) -> MagicMock:
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result


@pytest.mark.unit
class TestNotificationRepository:
    async def test_create(
        self, notif_repo: NotificationRepository, mock_session: AsyncMock
    ) -> None:
        result = await notif_repo.create(
            title="テスト通知",
            body="テスト本文",
            provider="slack",
            tenant_id="t-001",
        )
        assert mock_session.add.called
        assert mock_session.flush.called
        assert isinstance(result, Notification)

    async def test_get_by_project(
        self, notif_repo: NotificationRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars(
            [MagicMock(spec=Notification)]
        )
        results = await notif_repo.get_by_project("t-001", "proj-001")
        assert len(results) == 1
        assert mock_session.execute.called

    async def test_get_by_project_empty(
        self, notif_repo: NotificationRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars([])
        results = await notif_repo.get_by_project("t-001", "proj-999")
        assert len(results) == 0

    async def test_get_failed(
        self, notif_repo: NotificationRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars(
            [MagicMock(spec=Notification), MagicMock(spec=Notification)]
        )
        results = await notif_repo.get_failed("t-001")
        assert len(results) == 2


@pytest.mark.unit
class TestNotificationSettingRepository:
    async def test_create(
        self, setting_repo: NotificationSettingRepository, mock_session: AsyncMock
    ) -> None:
        result = await setting_repo.create(
            provider="slack",
            channel="#audit-alerts",
            tenant_id="t-001",
        )
        assert isinstance(result, NotificationSetting)

    async def test_get_enabled(
        self, setting_repo: NotificationSettingRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars(
            [MagicMock(spec=NotificationSetting)]
        )
        results = await setting_repo.get_enabled("t-001")
        assert len(results) == 1
