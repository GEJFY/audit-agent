"""RBAC テスト"""

import pytest

from src.security.rbac import Permission, RBACService


@pytest.mark.unit
class TestRBACService:
    """RBACサービスのユニットテスト"""

    def test_admin_has_all_permissions(self, rbac_service: RBACService) -> None:
        """管理者は全権限を持つ"""
        assert rbac_service.has_permission("admin", "project:read")
        assert rbac_service.has_permission("admin", "admin:users")
        assert rbac_service.has_permission("admin", "admin:tenants")

    def test_auditor_permissions(self, rbac_service: RBACService) -> None:
        """監査人の権限"""
        assert rbac_service.has_permission("auditor", "project:read")
        assert rbac_service.has_permission("auditor", "project:create")
        assert rbac_service.has_permission("auditor", "agent:execute")
        assert rbac_service.has_permission("auditor", "report:create")
        # 管理者権限は持たない
        assert not rbac_service.has_permission("auditor", "admin:users")
        assert not rbac_service.has_permission("auditor", "admin:tenants")

    def test_auditee_manager_permissions(self, rbac_service: RBACService) -> None:
        """被監査部門長の権限"""
        assert rbac_service.has_permission("auditee_manager", "dialogue:approve")
        assert rbac_service.has_permission("auditee_manager", "evidence:upload")
        assert rbac_service.has_permission("auditee_manager", "agent:execute")
        # プロジェクト作成はできない
        assert not rbac_service.has_permission("auditee_manager", "project:create")

    def test_auditee_user_permissions(self, rbac_service: RBACService) -> None:
        """被監査担当者の権限"""
        assert rbac_service.has_permission("auditee_user", "dialogue:send")
        assert rbac_service.has_permission("auditee_user", "evidence:upload")
        # 承認はできない
        assert not rbac_service.has_permission("auditee_user", "dialogue:approve")

    def test_viewer_permissions(self, rbac_service: RBACService) -> None:
        """閲覧者の権限"""
        assert rbac_service.has_permission("viewer", "project:read")
        assert rbac_service.has_permission("viewer", "report:read")
        # 書き込み系はできない
        assert not rbac_service.has_permission("viewer", "project:create")
        assert not rbac_service.has_permission("viewer", "evidence:upload")

    def test_invalid_role(self, rbac_service: RBACService) -> None:
        """無効なロール"""
        assert not rbac_service.has_permission("nonexistent", "project:read")

    def test_get_permissions(self, rbac_service: RBACService) -> None:
        """権限一覧取得"""
        perms = rbac_service.get_permissions("auditor")
        assert "project:read" in perms
        assert "agent:execute" in perms

    def test_get_permissions_invalid_role(self, rbac_service: RBACService) -> None:
        """無効ロールの権限一覧は空"""
        perms = rbac_service.get_permissions("invalid")
        assert len(perms) == 0

    def test_check_permission_success(self, rbac_service: RBACService) -> None:
        """権限チェック成功"""
        # PermissionErrorが発生しないこと
        rbac_service.check_permission("admin", "admin:users")

    def test_check_permission_failure(self, rbac_service: RBACService) -> None:
        """権限チェック失敗"""
        with pytest.raises(PermissionError, match="does not have permission"):
            rbac_service.check_permission("viewer", "admin:users")


@pytest.mark.unit
class TestPermission:
    """Permissionデータクラスのテスト"""

    def test_str(self) -> None:
        p = Permission("project", "read")
        assert str(p) == "project:read"

    def test_frozen(self) -> None:
        p = Permission("project", "read")
        with pytest.raises(AttributeError):
            p.resource = "other"  # type: ignore[misc]
