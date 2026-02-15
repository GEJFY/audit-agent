"""ヘルスチェックテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.monitoring.health import (
    ComponentHealth,
    HealthChecker,
    HealthStatus,
    SystemHealth,
)


@pytest.mark.unit
class TestHealthStatus:
    """HealthStatus enumのテスト"""

    def test_values(self) -> None:
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


@pytest.mark.unit
class TestComponentHealth:
    """ComponentHealthのテスト"""

    def test_defaults(self) -> None:
        c = ComponentHealth(name="test", status=HealthStatus.HEALTHY)
        assert c.details == {}
        assert c.latency_ms == 0.0

    def test_with_details(self) -> None:
        c = ComponentHealth(
            name="db",
            status=HealthStatus.HEALTHY,
            details={"pool_size": 10},
            latency_ms=5.5,
        )
        assert c.details["pool_size"] == 10
        assert c.latency_ms == 5.5


@pytest.mark.unit
class TestSystemHealth:
    """SystemHealthのテスト"""

    def test_to_dict(self) -> None:
        """辞書変換"""
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            components=[
                ComponentHealth(name="db", status=HealthStatus.HEALTHY, latency_ms=3.14),
            ],
            version="1.0.0",
        )
        d = health.to_dict()
        assert d["status"] == "healthy"
        assert d["version"] == "1.0.0"
        assert len(d["components"]) == 1
        assert d["components"][0]["name"] == "db"
        assert d["components"][0]["latency_ms"] == 3.14

    def test_to_dict_empty_components(self) -> None:
        """コンポーネントなし"""
        health = SystemHealth(status=HealthStatus.HEALTHY, components=[])
        d = health.to_dict()
        assert d["components"] == []


@pytest.mark.unit
class TestHealthChecker:
    """HealthCheckerのテスト"""

    async def test_check_database_healthy(self) -> None:
        """DB正常"""
        checker = HealthChecker()
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_engine.connect = MagicMock(return_value=mock_conn)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock()
        mock_engine.pool.size.return_value = 5

        result = await checker.check_database(mock_engine)
        assert result.name == "postgresql"
        assert result.status == HealthStatus.HEALTHY

    async def test_check_database_unhealthy(self) -> None:
        """DB異常"""
        checker = HealthChecker()
        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(side_effect=Exception("Connection refused"))

        result = await checker.check_database(mock_engine)
        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.details

    async def test_check_redis_healthy(self) -> None:
        """Redis正常"""
        checker = HealthChecker()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.info = AsyncMock(return_value={"redis_version": "7.0"})

        result = await checker.check_redis(mock_redis)
        assert result.name == "redis"
        assert result.status == HealthStatus.HEALTHY
        assert result.details["version"] == "7.0"

    async def test_check_redis_unhealthy(self) -> None:
        """Redis異常"""
        checker = HealthChecker()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))

        result = await checker.check_redis(mock_redis)
        assert result.status == HealthStatus.UNHEALTHY

    async def test_check_all_healthy(self) -> None:
        """全コンポーネント正常"""
        checker = HealthChecker()

        with patch.object(checker, "check_database") as mock_db, patch.object(
            checker, "check_redis"
        ) as mock_redis:
            mock_db.return_value = ComponentHealth(name="db", status=HealthStatus.HEALTHY)
            mock_redis.return_value = ComponentHealth(name="redis", status=HealthStatus.HEALTHY)

            result = await checker.check_all(engine=MagicMock(), redis_client=MagicMock())

            assert result.status == HealthStatus.HEALTHY
            assert len(result.components) == 2

    async def test_check_all_unhealthy(self) -> None:
        """一部コンポーネント異常"""
        checker = HealthChecker()

        with patch.object(checker, "check_database") as mock_db, patch.object(
            checker, "check_redis"
        ) as mock_redis:
            mock_db.return_value = ComponentHealth(name="db", status=HealthStatus.HEALTHY)
            mock_redis.return_value = ComponentHealth(name="redis", status=HealthStatus.UNHEALTHY)

            result = await checker.check_all(engine=MagicMock(), redis_client=MagicMock())

            assert result.status == HealthStatus.UNHEALTHY

    async def test_check_all_degraded(self) -> None:
        """一部コンポーネント劣化"""
        checker = HealthChecker()

        with patch.object(checker, "check_database") as mock_db:
            mock_db.return_value = ComponentHealth(name="db", status=HealthStatus.DEGRADED)

            result = await checker.check_all(engine=MagicMock())

            assert result.status == HealthStatus.DEGRADED

    async def test_check_all_no_components(self) -> None:
        """コンポーネントなし（全てNone）"""
        checker = HealthChecker()
        result = await checker.check_all()
        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 0
