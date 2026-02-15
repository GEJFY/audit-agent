"""DialogueRepository テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.dialogue import DialogueMessage
from src.db.repositories.dialogue import DialogueRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> DialogueRepository:
    return DialogueRepository(session=mock_session)


@pytest.mark.unit
class TestDialogueRepository:
    async def test_get_thread(self, repo: DialogueRepository, mock_session: AsyncMock) -> None:
        """スレッド取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(spec=DialogueMessage)]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_thread("thread-001")
        assert mock_session.execute.called
        assert len(results) == 1

    async def test_get_by_project(self, repo: DialogueRepository, mock_session: AsyncMock) -> None:
        """プロジェクト対話取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_project("project-001")
        assert mock_session.execute.called
        assert isinstance(results, list)

    async def test_get_pending_approvals(self, repo: DialogueRepository, mock_session: AsyncMock) -> None:
        """承認待ちメッセージ取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(spec=DialogueMessage)]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_pending_approvals("tenant-001")
        assert mock_session.execute.called
        assert len(results) == 1

    async def test_get_escalated(self, repo: DialogueRepository, mock_session: AsyncMock) -> None:
        """エスカレーション取得"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.get_escalated("tenant-001")
        assert mock_session.execute.called
        assert isinstance(results, list)
