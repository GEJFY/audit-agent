"""FastAPI メインアプリケーション"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_client import make_asgi_app

from src import __version__
from src.api.middleware.correlation import CorrelationIdMiddleware
from src.api.middleware.rate_limit import setup_rate_limiter
from src.api.middleware.security import (
    IPThrottleMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)
from src.api.routes import agents, auth, compliance, dialogue, evidence, health, projects, websocket
from src.config.settings import get_settings
from src.monitoring.logging import setup_logging
from src.monitoring.metrics import app_info


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションライフサイクル管理"""
    settings = get_settings()

    # ログ設定
    setup_logging(
        level=settings.app_log_level,
        json_output=settings.is_production,
    )

    logger.info(
        "audit-agent 起動",
        version=__version__,
        env=settings.app_env,
    )

    # メトリクス情報設定
    app_info.info(
        {
            "version": __version__,
            "environment": settings.app_env,
        }
    )

    # 外部監視統合（Sentry, Datadog, LangSmith）
    from src.monitoring.integrations import setup_all_integrations

    setup_all_integrations()

    # Kafka Consumer起動（バックグラウンド）
    kafka_task = None
    if settings.kafka_bootstrap_servers:
        try:
            from src.dialogue.kafka_bus import get_kafka_bus

            kafka_bus = get_kafka_bus()
            kafka_task = asyncio.create_task(kafka_bus.start_consumer())
            logger.info("Kafka Consumer起動")
        except Exception as e:
            logger.warning("Kafka Consumer起動スキップ: {}", str(e))

    yield

    # Kafka Consumer停止
    if kafka_task:
        kafka_task.cancel()
        try:
            from src.dialogue.kafka_bus import get_kafka_bus

            await get_kafka_bus().disconnect()
        except Exception:
            logger.debug("Kafka Consumer停止時エラー")

    logger.info("audit-agent シャットダウン")


def create_app() -> FastAPI:
    """FastAPIアプリケーションファクトリ"""
    settings = get_settings()

    app = FastAPI(
        title="audit-agent API",
        description="双方向AI監査エージェントプラットフォーム",
        version=__version__,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── ミドルウェア ──────────────────────────────────
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # セキュリティヘッダー
    app.add_middleware(SecurityHeadersMiddleware)

    # リクエストバリデーション（SQLi/XSS防御）
    app.add_middleware(RequestValidationMiddleware)

    # IP単位スロットリング
    if settings.is_production:
        app.add_middleware(IPThrottleMiddleware)

    # 相関ID
    app.add_middleware(CorrelationIdMiddleware)

    # レート制限
    setup_rate_limiter(app)

    # ── ルーター ──────────────────────────────────────
    api_prefix = "/api/v1"
    app.include_router(health.router, prefix=api_prefix, tags=["health"])
    app.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["auth"])
    app.include_router(projects.router, prefix=f"{api_prefix}/projects", tags=["projects"])
    app.include_router(agents.router, prefix=f"{api_prefix}/agents", tags=["agents"])
    app.include_router(dialogue.router, prefix=f"{api_prefix}/dialogue", tags=["dialogue"])
    app.include_router(evidence.router, prefix=f"{api_prefix}/evidence", tags=["evidence"])
    app.include_router(compliance.router, prefix=f"{api_prefix}/compliance", tags=["compliance"])

    # WebSocket
    app.include_router(websocket.router, prefix=f"{api_prefix}", tags=["websocket"])

    # ── Prometheusメトリクス ──────────────────────────
    if settings.prometheus_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


# アプリケーションインスタンス
app = create_app()


def run() -> None:
    """開発サーバー起動"""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.app_log_level.lower(),
    )
