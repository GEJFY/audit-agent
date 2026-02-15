"""FindingRepository テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.auditor import Finding
from src.db.repositories.finding import FindingRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> FindingRepository:
    return FindingRepository(session=mock_session)


@pytest.mark.unit
class TestFindingRepository:
    async def test_get_by_project(self, repo: FindingRepository, mock_session: AsyncMock) -> None:
        """プロジェクト別指摘事項取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(spec=Finding)]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_project("tenant-001", "project-001")
        assert mock_session.execute.called
        assert len(results) == 1

    async def test_get_by_project_empty(self, repo: FindingRepository, mock_session: AsyncMock) -> None:
        """指摘事項なし"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_project("tenant-001", "project-001")
        assert len(results) == 0

    async def test_get_risk_summary(self, repo: FindingRepository, mock_session: AsyncMock) -> None:
        """リスクサマリー取得"""
        mock_result = MagicMock()
        mock_result.all.return_value = [("high", 3), ("medium", 5), ("low", 2)]
        mock_session.execute.return_value = mock_result

        summary = await repo.get_risk_summary("tenant-001", "project-001")
        assert mock_session.execute.called
        assert isinstance(summary, dict)
