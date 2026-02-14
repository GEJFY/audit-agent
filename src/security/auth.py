"""JWT認証サービス — トークン発行・検証"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from loguru import logger
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config.settings import get_settings


class TokenPayload(BaseModel):
    """JWTトークンペイロード"""

    sub: str  # user_id
    tenant_id: str  # テナントID
    role: str  # ユーザーロール
    exp: datetime  # 有効期限
    iat: datetime  # 発行日時
    jti: str  # トークンID（ユニーク）
    token_type: str  # access / refresh


class TokenPair(BaseModel):
    """アクセストークン + リフレッシュトークンのペア"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int  # アクセストークン有効期限（秒）


class AuthService:
    """認証サービス — パスワードハッシュ化 + JWT管理"""

    def __init__(self) -> None:
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._settings = get_settings()

    def hash_password(self, password: str) -> str:
        """パスワードをbcryptハッシュ化"""
        return self._pwd_context.hash(password)  # type: ignore[no-any-return]

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """パスワード検証"""
        return self._pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]

    def create_token_pair(
        self,
        user_id: UUID,
        tenant_id: UUID,
        role: str,
    ) -> TokenPair:
        """アクセス + リフレッシュトークンペアを発行"""
        import uuid

        now = datetime.now(UTC)

        # アクセストークン
        access_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "exp": now + timedelta(minutes=self._settings.jwt_access_token_expire_minutes),
            "iat": now,
            "jti": str(uuid.uuid4()),
            "token_type": "access",
        }
        access_token = jwt.encode(
            access_payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

        # リフレッシュトークン
        refresh_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role,
            "exp": now + timedelta(days=self._settings.jwt_refresh_token_expire_days),
            "iat": now,
            "jti": str(uuid.uuid4()),
            "token_type": "refresh",
        }
        refresh_token = jwt.encode(
            refresh_payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

        logger.info(
            "トークンペア発行",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            role=role,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.jwt_access_token_expire_minutes * 60,
        )

    def verify_token(self, token: str, expected_type: str = "access") -> TokenPayload:
        """JWTトークンを検証してペイロードを返す

        Raises:
            jwt.ExpiredSignatureError: トークン有効期限切れ
            jwt.InvalidTokenError: 不正なトークン
            ValueError: トークンタイプ不一致
        """
        payload: dict[str, Any] = jwt.decode(
            token,
            self._settings.jwt_secret_key,
            algorithms=[self._settings.jwt_algorithm],
        )

        if payload.get("token_type") != expected_type:
            raise ValueError(f"Expected token type '{expected_type}', got '{payload.get('token_type')}'")

        return TokenPayload(
            sub=payload["sub"],
            tenant_id=payload["tenant_id"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
            iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            jti=payload["jti"],
            token_type=payload["token_type"],
        )


def verify_token(token: str) -> dict[str, Any]:
    """トークン検証ヘルパー（モジュールレベル）"""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    return payload
