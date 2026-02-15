"""テナントミドルウェアテスト"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.api.middleware.tenant import get_current_tenant_id
from src.security.auth import TokenPayload


@pytest.mark.unit
class TestTenantMiddleware:
    async def test_get_tenant_id(self) -> None:
        """トークンからテナントID取得"""
        user = TokenPayload(
            sub="user-001",
            tenant_id="tenant-001",
            role="admin",
            exp=datetime(2099, 12, 31, tzinfo=UTC),
            iat=datetime.now(UTC),
            jti=str(uuid4()),
            token_type="access",
        )
        tenant_id = await get_current_tenant_id(user=user)
        assert tenant_id == "tenant-001"
