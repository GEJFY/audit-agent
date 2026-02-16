"""プロジェクトエンドポイントテスト"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestProjectRoutes:
    async def test_list_projects_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """プロジェクト一覧 — 空"""
        # count query
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 0
        # list query
        mock_list = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_list])

        resp = await client.get("/api/v1/projects/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_create_project_invalid_body(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """プロジェクト作成 — バリデーションエラー（必須フィールド不足）"""
        resp = await client.post(
            "/api/v1/projects/",
            json={"name": "テスト"},  # fiscal_year, audit_type missing
        )
        assert resp.status_code == 422

    async def test_get_project_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ) -> None:
        """存在しないプロジェクト取得"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        resp = await client.get(f"/api/v1/projects/{uuid4()}")
        assert resp.status_code == 404
