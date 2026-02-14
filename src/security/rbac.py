"""ロールベースアクセス制御（RBAC）"""

from dataclasses import dataclass

from src.config.constants import UserRole


@dataclass(frozen=True)
class Permission:
    """操作権限定義"""

    resource: str
    action: str  # read, create, update, delete, execute, approve

    def __str__(self) -> str:
        return f"{self.resource}:{self.action}"


# ── 権限定義 ──────────────────────────────────────────
PERMISSIONS = {
    # 監査プロジェクト
    "project:read": Permission("project", "read"),
    "project:create": Permission("project", "create"),
    "project:update": Permission("project", "update"),
    "project:delete": Permission("project", "delete"),
    # エージェント操作
    "agent:execute": Permission("agent", "execute"),
    "agent:configure": Permission("agent", "configure"),
    "agent:approve": Permission("agent", "approve"),
    # 対話
    "dialogue:read": Permission("dialogue", "read"),
    "dialogue:send": Permission("dialogue", "send"),
    "dialogue:approve": Permission("dialogue", "approve"),
    # 証跡
    "evidence:read": Permission("evidence", "read"),
    "evidence:upload": Permission("evidence", "upload"),
    "evidence:download": Permission("evidence", "download"),
    # 報告書
    "report:read": Permission("report", "read"),
    "report:create": Permission("report", "create"),
    "report:approve": Permission("report", "approve"),
    # 管理
    "admin:users": Permission("admin", "users"),
    "admin:tenants": Permission("admin", "tenants"),
    "admin:settings": Permission("admin", "settings"),
}

# ── ロール別権限マッピング ────────────────────────────
ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.ADMIN: set(PERMISSIONS.keys()),
    UserRole.AUDITOR: {
        "project:read",
        "project:create",
        "project:update",
        "agent:execute",
        "agent:configure",
        "agent:approve",
        "dialogue:read",
        "dialogue:send",
        "dialogue:approve",
        "evidence:read",
        "evidence:download",
        "report:read",
        "report:create",
        "report:approve",
    },
    UserRole.AUDITEE_MANAGER: {
        "project:read",
        "dialogue:read",
        "dialogue:send",
        "dialogue:approve",
        "evidence:read",
        "evidence:upload",
        "evidence:download",
        "agent:execute",
    },
    UserRole.AUDITEE_USER: {
        "project:read",
        "dialogue:read",
        "dialogue:send",
        "evidence:read",
        "evidence:upload",
    },
    UserRole.VIEWER: {
        "project:read",
        "dialogue:read",
        "evidence:read",
        "report:read",
    },
}


class RBACService:
    """RBAC権限チェックサービス"""

    def has_permission(self, role: str, permission_key: str) -> bool:
        """指定ロールが指定権限を持つか"""
        try:
            user_role = UserRole(role)
        except ValueError:
            return False
        return permission_key in ROLE_PERMISSIONS.get(user_role, set())

    def get_permissions(self, role: str) -> set[str]:
        """指定ロールの全権限を返す"""
        try:
            user_role = UserRole(role)
        except ValueError:
            return set()
        return ROLE_PERMISSIONS.get(user_role, set())

    def check_permission(self, role: str, permission_key: str) -> None:
        """権限チェック。不正アクセス時はPermissionError送出

        Raises:
            PermissionError: 権限なし
        """
        if not self.has_permission(role, permission_key):
            raise PermissionError(f"Role '{role}' does not have permission '{permission_key}'")
