"""JWT認証ミドルウェア"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.security.auth import AuthService, TokenPayload
from src.security.rbac import RBACService

security = HTTPBearer()
_auth_service = AuthService()
_rbac_service = RBACService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """現在のユーザーをJWTトークンから取得"""
    try:
        payload = _auth_service.verify_token(credentials.credentials)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"認証エラー: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(permission: str):  # type: ignore[no-untyped-def]
    """権限チェックの依存性注入デコレータ"""

    async def _check(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not _rbac_service.has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限不足: {permission}",
            )
        return user

    return _check
