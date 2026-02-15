"""FastAPI 依存性注入"""

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.llm_gateway.gateway import LLMGateway
from src.llm_gateway.providers.anthropic import AnthropicProvider


async def get_db_session() -> AsyncSession:  # type: ignore[misc]
    """DBセッション依存性"""
    async for session in get_session():
        yield session


def get_llm_gateway() -> LLMGateway:
    """LLMゲートウェイ依存性"""
    gateway = LLMGateway()
    gateway.register_provider(AnthropicProvider())
    return gateway


async def get_current_user_ws(token: str) -> dict[str, Any] | None:
    """WebSocket用トークン検証"""
    if not token:
        return None
    try:
        from src.security.auth import verify_token

        payload = verify_token(token)
        return {
            "user_id": payload.get("sub", ""),
            "tenant_id": payload.get("tenant_id", ""),
            "role": payload.get("role", "viewer"),
        }
    except Exception as e:
        logger.debug("WebSocket認証エラー: {}", str(e))
        return None
