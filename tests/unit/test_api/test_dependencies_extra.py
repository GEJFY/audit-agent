"""依存性注入 get_db_session / get_current_user_ws の追加テスト"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.unit
class TestGetDbSession:
    """get_db_session ジェネレータのテスト"""

    @pytest.mark.asyncio
    async def test_get_db_session_yields_session(self) -> None:
        """get_db_session がセッションを yield する"""
        mock_session = AsyncMock()

        async def mock_get_session():
            yield mock_session

        with patch("src.api.dependencies.get_session", return_value=mock_get_session()):
            from src.api.dependencies import get_db_session

            sessions = []
            async for session in get_db_session():
                sessions.append(session)

        assert len(sessions) == 1
        assert sessions[0] is mock_session

    @pytest.mark.asyncio
    async def test_get_db_session_iterates_underlying_generator(self) -> None:
        """get_db_session は get_session の非同期ジェネレータを消費する"""
        call_count = 0
        mock_session = AsyncMock()

        async def mock_get_session():
            nonlocal call_count
            call_count += 1
            yield mock_session

        with patch("src.api.dependencies.get_session", return_value=mock_get_session()):
            from src.api.dependencies import get_db_session

            async for _ in get_db_session():
                pass

        assert call_count == 1


@pytest.mark.unit
class TestGetCurrentUserWs:
    """get_current_user_ws WebSocket認証のテスト"""

    @pytest.mark.asyncio
    async def test_empty_token_returns_none(self) -> None:
        """空トークンは None を返す"""
        from src.api.dependencies import get_current_user_ws

        result = await get_current_user_ws("")
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_dict(self) -> None:
        """有効なトークンはユーザー辞書を返す"""
        mock_payload = {
            "sub": "user-123",
            "tenant_id": "tenant-456",
            "role": "auditor",
        }

        with patch("src.security.auth.verify_token", return_value=mock_payload):
            from src.api.dependencies import get_current_user_ws

            result = await get_current_user_ws("valid.jwt.token")

        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["role"] == "auditor"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self) -> None:
        """不正なトークンは None を返す（例外をキャッチ）"""
        with patch("src.security.auth.verify_token", side_effect=Exception("invalid token")):
            from src.api.dependencies import get_current_user_ws

            result = await get_current_user_ws("bad.token.here")

        assert result is None

    @pytest.mark.asyncio
    async def test_token_missing_optional_fields_uses_defaults(self) -> None:
        """ペイロードのオプションフィールド欠落時にデフォルト値を使う"""
        # sub / tenant_id / role が存在しないペイロード
        mock_payload: dict = {}

        with patch("src.security.auth.verify_token", return_value=mock_payload):
            from src.api.dependencies import get_current_user_ws

            result = await get_current_user_ws("some.token")

        assert result is not None
        assert result["user_id"] == ""
        assert result["tenant_id"] == ""
        assert result["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_exception_is_logged_and_none_returned(self) -> None:
        """例外発生時に logger.debug が呼ばれ None が返る"""
        with (
            patch("src.security.auth.verify_token", side_effect=ValueError("jwt error")),
            patch("src.api.dependencies.logger") as mock_logger,
        ):
            from src.api.dependencies import get_current_user_ws

            result = await get_current_user_ws("bad.token")

        assert result is None
        mock_logger.debug.assert_called_once()
