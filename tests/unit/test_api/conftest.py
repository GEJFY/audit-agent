"""API テスト共通フィクスチャ"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.security.auth import TokenPayload


@pytest.fixture
def mock_token_payload() -> TokenPayload:
    """テスト用トークンペイロード"""
    return TokenPayload(
        sub=str(uuid4()),
        tenant_id=str(uuid4()),
        role="admin",
        exp=datetime(2099, 12, 31, tzinfo=UTC),
        iat=datetime.now(UTC),
        jti=str(uuid4()),
        token_type="access",
    )


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """モックDBセッション"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def test_app(mock_db_session: AsyncMock, mock_token_payload: TokenPayload) -> Any:
    """テスト用FastAPIアプリ（依存性オーバーライド済み）"""
    from src.api.dependencies import get_db_session
    from src.api.main import create_app
    from src.api.middleware.auth import get_current_user, require_permission

    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[get_current_user] = lambda: mock_token_payload

    # require_permission は関数を返すデコレータなので、全権限を許可
    def _mock_require_permission(permission: str) -> Any:
        async def _inner() -> TokenPayload:
            return mock_token_payload

        return _inner

    app.dependency_overrides[require_permission] = _mock_require_permission

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app: Any) -> AsyncGenerator[AsyncClient, None]:
    """テスト用HTTPクライアント"""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
