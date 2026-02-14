"""認証サービス テスト"""

import pytest
from uuid import uuid4

from src.security.auth import AuthService


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService()


@pytest.mark.unit
class TestAuthService:
    """認証サービスのユニットテスト"""

    def test_hash_password(self, auth_service: AuthService) -> None:
        """パスワードハッシュ化テスト"""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_password(self, auth_service: AuthService) -> None:
        """パスワード検証テスト"""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("WrongPassword", hashed) is False

    def test_create_token_pair(self, auth_service: AuthService) -> None:
        """トークンペア発行テスト"""
        user_id = uuid4()
        tenant_id = uuid4()

        pair = auth_service.create_token_pair(user_id, tenant_id, "auditor")

        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    def test_verify_access_token(self, auth_service: AuthService) -> None:
        """アクセストークン検証テスト"""
        user_id = uuid4()
        tenant_id = uuid4()

        pair = auth_service.create_token_pair(user_id, tenant_id, "admin")
        payload = auth_service.verify_token(pair.access_token)

        assert payload.sub == str(user_id)
        assert payload.tenant_id == str(tenant_id)
        assert payload.role == "admin"
        assert payload.token_type == "access"

    def test_verify_refresh_token(self, auth_service: AuthService) -> None:
        """リフレッシュトークン検証テスト"""
        user_id = uuid4()
        tenant_id = uuid4()

        pair = auth_service.create_token_pair(user_id, tenant_id, "auditor")
        payload = auth_service.verify_token(pair.refresh_token, expected_type="refresh")

        assert payload.sub == str(user_id)
        assert payload.token_type == "refresh"

    def test_verify_wrong_token_type(self, auth_service: AuthService) -> None:
        """トークンタイプ不一致テスト"""
        pair = auth_service.create_token_pair(uuid4(), uuid4(), "admin")

        with pytest.raises(ValueError, match="Expected token type"):
            auth_service.verify_token(pair.refresh_token, expected_type="access")
