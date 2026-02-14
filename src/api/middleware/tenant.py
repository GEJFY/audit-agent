"""テナント識別ミドルウェア"""

from fastapi import Depends, HTTPException, status

from src.security.auth import TokenPayload
from src.api.middleware.auth import get_current_user


async def get_current_tenant_id(
    user: TokenPayload = Depends(get_current_user),
) -> str:
    """現在のテナントIDを取得"""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="テナントIDが未設定",
        )
    return user.tenant_id
