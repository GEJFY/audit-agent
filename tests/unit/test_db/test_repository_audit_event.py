"""AuditEventRepository テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.audit_event import AuditEvent
from src.db.repositories.audit_event import AuditEventRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> AuditEventRepository:
    return AuditEventRepository(session=mock_session)


def _mock_scalars(items: list) -> MagicMock:
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result


@pytest.mark.unit
class TestAuditEventRepository:
    async def test_create(
        self, repo: AuditEventRepository, mock_session: AsyncMock
    ) -> None:
        result = await repo.create(
            event_type="create",
            resource_type="project",
            tenant_id="t-001",
        )
        assert mock_session.add.called
        assert isinstance(result, AuditEvent)

    async def test_get_by_resource(
        self, repo: AuditEventRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars(
            [MagicMock(spec=AuditEvent)]
        )
        results = await repo.get_by_resource("t-001", "project", "proj-001")
        assert len(results) == 1

    async def test_get_by_resource_empty(
        self, repo: AuditEventRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars([])
        results = await repo.get_by_resource("t-001", "finding", "f-999")
        assert len(results) == 0

    async def test_get_by_actor(
        self, repo: AuditEventRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars(
            [MagicMock(spec=AuditEvent), MagicMock(spec=AuditEvent)]
        )
        results = await repo.get_by_actor("t-001", "user-001")
        assert len(results) == 2

    async def test_get_by_project(
        self, repo: AuditEventRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars(
            [MagicMock(spec=AuditEvent)]
        )
        results = await repo.get_by_project("t-001", "proj-001")
        assert len(results) == 1

    async def test_get_by_actor_with_limit(
        self, repo: AuditEventRepository, mock_session: AsyncMock
    ) -> None:
        mock_session.execute.return_value = _mock_scalars([])
        results = await repo.get_by_actor("t-001", "user-001", limit=10)
        assert len(results) == 0
        assert mock_session.execute.called
