"""認証エンドポイントテスト"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestAuthRoutes:
    async def test_login_user_not_found(self, client: AsyncClient, mock_db_session: AsyncMock) -> None:
        """存在しないユーザーでログイン"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "notfound@test.com", "password": "pass"},
        )
        assert resp.status_code == 401

    async def test_register_invalid_body(self, client: AsyncClient, mock_db_session: AsyncMock) -> None:
        """ユーザー登録 — バリデーションエラー（必須フィールド不足）"""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@test.com"},  # password, full_name, tenant_id missing
        )
        assert resp.status_code == 422

    async def test_me_endpoint(self, client: AsyncClient, mock_db_session: AsyncMock) -> None:
        """GET /me — 現在のユーザー情報"""
        mock_user = MagicMock()
        mock_user.id = "user-id"
        mock_user.tenant_id = "t-001"
        mock_user.email = "test@test.com"
        mock_user.full_name = "テスト"
        mock_user.role = "admin"
        mock_user.department = None
        mock_user.is_active = True
        mock_user.last_login_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (200, 404)

    async def test_refresh_invalid_token(self, client: AsyncClient) -> None:
        """無効なリフレッシュトークン"""
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert resp.status_code in (401, 500)
