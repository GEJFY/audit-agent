"""SQLAlchemy async engine — コネクションプール管理"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.config.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """AsyncEngineシングルトンを返す"""
    settings = get_settings()

    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.app_debug and settings.is_development,
    )

    return engine
