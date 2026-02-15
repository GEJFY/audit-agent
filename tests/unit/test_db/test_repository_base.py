"""BaseRepository テスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models.auditor import AuditProject
from src.db.repositories.base import BaseRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    # add はsyncメソッド
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> BaseRepository:
    return BaseRepository(model=AuditProject, session=mock_session)


@pytest.mark.unit
class TestBaseRepository:
    """BaseRepository CRUDテスト"""

    async def test_create(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """レコード作成 — addしてflush"""
        result = await repo.create(
            name="テストプロジェクト",
            fiscal_year=2026,
            audit_type="j-sox",
            tenant_id="tenant-001",
        )

        assert mock_session.add.called
        assert mock_session.flush.called
        assert isinstance(result, AuditProject)

    async def test_get_by_id(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """ID検索"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(spec=AuditProject)
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id("test-id")

        assert mock_session.execute.called
        assert result is not None

    async def test_get_by_id_not_found(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """ID検索 — 未存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_id("nonexistent-id")
        assert result is None

    async def test_get_by_id_with_tenant(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """テナントID付きID検索"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(spec=AuditProject)
        mock_session.execute.return_value = mock_result

        await repo.get_by_id("test-id", tenant_id="tenant-001")
        assert mock_session.execute.called

    async def test_list_default(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """一覧取得（デフォルト）"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(spec=AuditProject)]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.list()
        assert mock_session.execute.called
        assert len(results) == 1

    async def test_list_with_tenant_filter(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """テナントフィルタ付き一覧"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        results = await repo.list(tenant_id="tenant-001")
        assert mock_session.execute.called
        assert isinstance(results, list)

    async def test_list_with_pagination(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """ページネーション付き一覧"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        await repo.list(offset=10, limit=5)
        assert mock_session.execute.called

    async def test_update(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """レコード更新 — execute with returning"""
        existing = MagicMock(spec=AuditProject)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await repo.update("test-id", name="更新名")
        assert mock_session.execute.called
        assert result is not None

    async def test_update_not_found(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """存在しないレコード更新"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.update("nonexistent-id", name="更新名")
        assert result is None

    async def test_delete(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """レコード削除 — rowcount > 0"""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repo.delete("test-id")
        assert mock_session.execute.called
        assert result is True

    async def test_delete_not_found(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """存在しないレコード削除 — rowcount = 0"""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repo.delete("nonexistent-id")
        assert result is False

    async def test_count(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """レコード数カウント"""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute.return_value = mock_result

        count = await repo.count()
        assert count == 42

    async def test_count_with_tenant(self, repo: BaseRepository, mock_session: AsyncMock) -> None:
        """テナント付きカウント"""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_session.execute.return_value = mock_result

        count = await repo.count(tenant_id="tenant-001")
        assert count == 10
