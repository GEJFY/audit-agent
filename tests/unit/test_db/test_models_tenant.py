"""Tenant / User DBモデル テスト"""

import pytest

from src.db.models.tenant import Tenant, User


def _has_column(model: type, name: str) -> bool:
    return name in model.__table__.columns


@pytest.mark.unit
class TestTenant:
    def test_tablename(self) -> None:
        assert Tenant.__tablename__ == "tenants"

    def test_has_required_columns(self) -> None:
        for col in ["id", "name", "tenant_type", "is_active", "settings"]:
            assert _has_column(Tenant, col), f"Missing column: {col}"

    def test_default_is_active(self) -> None:
        assert Tenant.__table__.columns["is_active"].default.arg is True

    def test_has_self_fk(self) -> None:
        """親テナントへの自己参照FK"""
        assert _has_column(Tenant, "parent_tenant_id")
        fks = [fk.target_fullname for fk in Tenant.__table__.columns["parent_tenant_id"].foreign_keys]
        assert "tenants.id" in fks

    def test_no_tenant_id_column(self) -> None:
        """TenantはBaseModelベース（tenant_id不要）"""
        assert not _has_column(Tenant, "tenant_id")


@pytest.mark.unit
class TestUser:
    def test_tablename(self) -> None:
        assert User.__tablename__ == "users"

    def test_has_required_columns(self) -> None:
        for col in ["tenant_id", "email", "hashed_password", "full_name", "role", "is_active"]:
            assert _has_column(User, col), f"Missing column: {col}"

    def test_email_unique(self) -> None:
        col = User.__table__.columns["email"]
        assert col.unique is True

    def test_email_indexed(self) -> None:
        col = User.__table__.columns["email"]
        assert col.index is True

    def test_default_is_active(self) -> None:
        assert User.__table__.columns["is_active"].default.arg is True

    def test_has_fk_tenant(self) -> None:
        fks = [fk.target_fullname for fk in User.__table__.columns["tenant_id"].foreign_keys]
        assert "tenants.id" in fks
