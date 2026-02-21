"""認証スキーマ UserResponse のユニットテスト"""

import pytest
from pydantic import ValidationError

from src.api.schemas.auth import UserResponse


@pytest.mark.unit
class TestUserResponse:
    """UserResponse Pydantic モデルのテスト"""

    def test_valid_user_response(self) -> None:
        """全フィールド正常入力でインスタンスを生成できる"""
        user = UserResponse(
            id="user-001",
            email="test@example.com",
            full_name="テスト ユーザー",
            role="auditor",
            tenant_id="tenant-001",
            is_active=True,
        )
        assert user.id == "user-001"
        assert user.email == "test@example.com"
        assert user.full_name == "テスト ユーザー"
        assert user.role == "auditor"
        assert user.tenant_id == "tenant-001"
        assert user.is_active is True

    def test_is_active_false(self) -> None:
        """is_active=False のユーザーを生成できる"""
        user = UserResponse(
            id="user-002",
            email="inactive@example.com",
            full_name="非アクティブ ユーザー",
            role="viewer",
            tenant_id="tenant-002",
            is_active=False,
        )
        assert user.is_active is False

    def test_missing_required_id_raises(self) -> None:
        """id フィールドがない場合 ValidationError が発生する"""
        with pytest.raises(ValidationError):
            UserResponse(  # type: ignore[call-arg]
                email="test@example.com",
                full_name="テスト",
                role="auditor",
                tenant_id="tenant-001",
                is_active=True,
            )

    def test_missing_required_email_raises(self) -> None:
        """email フィールドがない場合 ValidationError が発生する"""
        with pytest.raises(ValidationError):
            UserResponse(  # type: ignore[call-arg]
                id="user-001",
                full_name="テスト",
                role="auditor",
                tenant_id="tenant-001",
                is_active=True,
            )

    def test_missing_required_is_active_raises(self) -> None:
        """is_active フィールドがない場合 ValidationError が発生する"""
        with pytest.raises(ValidationError):
            UserResponse(  # type: ignore[call-arg]
                id="user-001",
                email="test@example.com",
                full_name="テスト",
                role="auditor",
                tenant_id="tenant-001",
            )

    def test_all_roles(self) -> None:
        """各種ロール文字列を受け入れる（文字列バリデーションなし）"""
        for role in ("admin", "auditor", "auditee_manager", "auditee_user", "viewer", "executive"):
            user = UserResponse(
                id="user-001",
                email="test@example.com",
                full_name="テスト",
                role=role,
                tenant_id="tenant-001",
                is_active=True,
            )
            assert user.role == role

    def test_model_dump(self) -> None:
        """model_dump() で辞書形式に変換できる"""
        user = UserResponse(
            id="user-001",
            email="test@example.com",
            full_name="テスト ユーザー",
            role="admin",
            tenant_id="tenant-001",
            is_active=True,
        )
        data = user.model_dump()
        assert data["id"] == "user-001"
        assert data["is_active"] is True
        assert set(data.keys()) == {"id", "email", "full_name", "role", "tenant_id", "is_active"}

    def test_is_active_coercion_from_int(self) -> None:
        """整数値が bool に型変換される（Pydantic v2 デフォルト動作）"""
        user = UserResponse(
            id="user-001",
            email="test@example.com",
            full_name="テスト",
            role="viewer",
            tenant_id="tenant-001",
            is_active=1,  # type: ignore[arg-type]
        )
        assert user.is_active is True
