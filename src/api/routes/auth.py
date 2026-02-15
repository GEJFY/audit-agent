"""認証エンドポイント — DB連携"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.middleware.auth import get_current_user
from src.db.models.tenant import User
from src.security.auth import AuthService, TokenPayload

router = APIRouter()
_auth_service = AuthService()


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "viewer"
    tenant_id: str
    department: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    department: str | None = None
    is_active: bool
    last_login_at: str | None = None


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """ログイン — DB認証 + JWTトークンペア発行"""
    result = await session.execute(select(User).where(User.email == request.email, User.is_active.is_(True)))  # type: ignore[call-arg]
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    if not _auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    user.last_login_at = datetime.now(UTC).isoformat()
    await session.commit()

    token_pair = _auth_service.create_token_pair(
        user_id=UUID(user.id),
        tenant_id=UUID(user.tenant_id),
        role=user.role,
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """ユーザー登録"""
    existing = await session.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このメールアドレスは既に登録されています",
        )

    hashed_password = _auth_service.hash_password(request.password)

    user = User(
        tenant_id=request.tenant_id,
        email=request.email,
        full_name=request.full_name,
        hashed_password=hashed_password,
        role=request.role,
        department=request.department,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department=user.department,
        is_active=user.is_active,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """トークンリフレッシュ"""
    try:
        payload = _auth_service.verify_token(request.refresh_token, expected_type="refresh")
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"リフレッシュトークンが無効: {err!s}",
        ) from err

    token_pair = _auth_service.create_token_pair(
        user_id=UUID(payload.sub),
        tenant_id=UUID(payload.tenant_id),
        role=payload.role,
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: TokenPayload = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """現在のユーザー情報"""
    result = await session.execute(select(User).where(User.id == user.sub))
    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    return UserResponse(
        user_id=db_user.id,
        tenant_id=db_user.tenant_id,
        email=db_user.email,
        full_name=db_user.full_name,
        role=db_user.role,
        department=db_user.department,
        is_active=db_user.is_active,
        last_login_at=db_user.last_login_at,
    )
