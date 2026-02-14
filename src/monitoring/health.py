"""ヘルスチェック — 依存サービスの状態確認"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from loguru import logger


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    details: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class SystemHealth:
    status: HealthStatus
    components: list[ComponentHealth]
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "version": self.version,
            "components": [
                {
                    "name": c.name,
                    "status": c.status,
                    "latency_ms": round(c.latency_ms, 2),
                    "details": c.details,
                }
                for c in self.components
            ],
        }


class HealthChecker:
    """依存サービスのヘルスチェックを実行"""

    async def check_database(self, engine: Any) -> ComponentHealth:
        """PostgreSQL接続チェック"""
        import time

        start = time.monotonic()
        try:
            from sqlalchemy import text

            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details={"pool_size": engine.pool.size()},
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.error("DB ヘルスチェック失敗", error=str(e))
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def check_redis(self, redis_client: Any) -> ComponentHealth:
        """Redis接続チェック"""
        import time

        start = time.monotonic()
        try:
            await redis_client.ping()
            latency = (time.monotonic() - start) * 1000
            info = await redis_client.info("server")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details={"version": info.get("redis_version", "unknown")},
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            logger.error("Redis ヘルスチェック失敗", error=str(e))
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                details={"error": str(e)},
            )

    async def check_all(
        self,
        engine: Any | None = None,
        redis_client: Any | None = None,
    ) -> SystemHealth:
        """全依存サービスのヘルスチェック"""
        from src import __version__

        components: list[ComponentHealth] = []

        if engine is not None:
            components.append(await self.check_database(engine))
        if redis_client is not None:
            components.append(await self.check_redis(redis_client))

        # 総合ステータス判定
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return SystemHealth(
            status=overall,
            components=components,
            version=__version__,
        )
