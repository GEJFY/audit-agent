"""ProjectRepository テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.auditor import AuditProject
from src.db.repositories.project import ProjectRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> ProjectRepository:
    return ProjectRepository(session=mock_session)


@pytest.mark.unit
class TestProjectRepository:
    async def test_get_active_projects(self, repo: ProjectRepository, mock_session: AsyncMock) -> None:
        """アクティブプロジェクト取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(spec=AuditProject)]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_active_projects("tenant-001")
        assert mock_session.execute.called
        assert len(results) == 1

    async def test_get_active_projects_empty(self, repo: ProjectRepository, mock_session: AsyncMock) -> None:
        """アクティブプロジェクトなし"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_active_projects("tenant-001")
        assert len(results) == 0

    async def test_get_by_fiscal_year(self, repo: ProjectRepository, mock_session: AsyncMock) -> None:
        """会計年度別取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(spec=AuditProject)]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_fiscal_year("tenant-001", 2026)
        assert mock_session.execute.called
        assert len(results) == 1
