"""JWT認証ミドルウェア get_current_user / require_permission のユニットテスト"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.security.auth import TokenPayload


def _make_token_payload(role: str = "admin") -> TokenPayload:
    """テスト用 TokenPayload を生成するヘルパー"""
    return TokenPayload(
        sub=str(uuid4()),
        tenant_id=str(uuid4()),
        role=role,
        exp=datetime(2099, 12, 31, tzinfo=UTC),
        iat=datetime.now(UTC),
        jti=str(uuid4()),
        token_type="access",
    )


@pytest.mark.unit
class TestGetCurrentUser:
    """get_current_user 依存性のテスト"""

    @pytest.mark.asyncio
    async def test_valid_credentials_returns_payload(self) -> None:
        """有効なトークンは TokenPayload を返す"""
        expected_payload = _make_token_payload(role="auditor")
        mock_credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid.jwt.token"

        with patch("src.api.middleware.auth._auth_service") as mock_auth:
            mock_auth.verify_token.return_value = expected_payload
            from src.api.middleware.auth import get_current_user

            result = await get_current_user(credentials=mock_credentials)

        assert result is expected_payload
        mock_auth.verify_token.assert_called_once_with("valid.jwt.token")

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self) -> None:
        """無効なトークンは HTTP 401 を発生させる"""
        mock_credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "bad.token"

        with patch("src.api.middleware.auth._auth_service") as mock_auth:
            mock_auth.verify_token.side_effect = ValueError("invalid token")
            from src.api.middleware.auth import get_current_user

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_credentials)

        assert exc_info.value.status_code == 401
        assert "認証エラー" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self) -> None:
        """期限切れトークンは HTTP 401 を発生させる"""
        import jwt

        mock_credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "expired.token"

        with patch("src.api.middleware.auth._auth_service") as mock_auth:
            mock_auth.verify_token.side_effect = jwt.ExpiredSignatureError("expired")
            from src.api.middleware.auth import get_current_user

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    async def test_401_includes_www_authenticate_header(self) -> None:
        """401 レスポンスに WWW-Authenticate: Bearer ヘッダーが含まれる"""
        mock_credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "bad.token"

        with patch("src.api.middleware.auth._auth_service") as mock_auth:
            mock_auth.verify_token.side_effect = Exception("any error")
            from src.api.middleware.auth import get_current_user

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_credentials)

        assert "Bearer" in exc_info.value.headers.get("WWW-Authenticate", "")


@pytest.mark.unit
class TestRequirePermission:
    """require_permission デコレータのテスト"""

    @pytest.mark.asyncio
    async def test_user_with_permission_passes(self) -> None:
        """権限を持つユーザーは TokenPayload をそのまま返す"""
        payload = _make_token_payload(role="admin")

        with patch("src.api.middleware.auth._rbac_service") as mock_rbac:
            mock_rbac.has_permission.return_value = True
            from src.api.middleware.auth import require_permission

            checker = require_permission("project:read")
            result = await checker(user=payload)

        assert result is payload
        mock_rbac.has_permission.assert_called_once_with("admin", "project:read")

    @pytest.mark.asyncio
    async def test_user_without_permission_raises_403(self) -> None:
        """権限を持たないユーザーは HTTP 403 を発生させる"""
        payload = _make_token_payload(role="viewer")

        with patch("src.api.middleware.auth._rbac_service") as mock_rbac:
            mock_rbac.has_permission.return_value = False
            from src.api.middleware.auth import require_permission

            checker = require_permission("admin:users")
            with pytest.raises(HTTPException) as exc_info:
                await checker(user=payload)

        assert exc_info.value.status_code == 403
        assert "admin:users" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_403_detail_includes_permission_name(self) -> None:
        """403 エラーの detail に権限名が含まれる"""
        payload = _make_token_payload(role="auditee_user")

        with patch("src.api.middleware.auth._rbac_service") as mock_rbac:
            mock_rbac.has_permission.return_value = False
            from src.api.middleware.auth import require_permission

            checker = require_permission("report:approve")
            with pytest.raises(HTTPException) as exc_info:
                await checker(user=payload)

        assert "report:approve" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_permission_returns_callable(self) -> None:
        """require_permission は呼び出し可能オブジェクトを返す"""
        from src.api.middleware.auth import require_permission

        checker = require_permission("project:read")
        assert callable(checker)

    @pytest.mark.asyncio
    async def test_different_permissions_checked_independently(self) -> None:
        """異なる権限キーが独立してチェックされる"""
        payload = _make_token_payload(role="auditor")

        with patch("src.api.middleware.auth._rbac_service") as mock_rbac:
            mock_rbac.has_permission.return_value = True
            from src.api.middleware.auth import require_permission

            checker_read = require_permission("project:read")
            checker_create = require_permission("project:create")

            await checker_read(user=payload)
            await checker_create(user=payload)

            assert mock_rbac.has_permission.call_count == 2
            calls = [c.args for c in mock_rbac.has_permission.call_args_list]
            permissions = [c[1] for c in calls]
            assert "project:read" in permissions
            assert "project:create" in permissions
