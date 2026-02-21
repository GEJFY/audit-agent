"""コネクタヘルスチェック・メトリクスルートテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app


def _make_mock_connector(healthy: bool = True, failure_count: int = 0) -> MagicMock:
    """ヘルスチェック用モックコネクタを生成"""
    mock = MagicMock()
    mock.health_check = AsyncMock(return_value=healthy)
    mock.circuit_breaker.is_open = False
    mock.circuit_breaker._failure_count = failure_count
    mock.circuit_breaker._failure_threshold = 5
    mock.circuit_breaker._cooldown_seconds = 60.0
    return mock


@pytest.mark.unit
class TestConnectorsHealthRoute:
    """GET /api/v1/connectors/health"""

    async def test_all_healthy(self) -> None:
        """全コネクタが正常な場合"""
        app = create_app()
        mock_check = AsyncMock(
            side_effect=[
                {"name": "sap", "status": "healthy", "latency_ms": 10.0, "circuit_breaker": {}},
                {"name": "box", "status": "healthy", "latency_ms": 5.0, "circuit_breaker": {}},
            ]
        )

        with (
            patch(
                "src.api.routes.connectors.CONNECTOR_CLASSES",
                {"sap": MagicMock, "box": MagicMock},
            ),
            patch("src.api.routes.connectors._check_single_connector", mock_check),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/connectors/health")

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["total"] == 2
            assert data["healthy"] == 2

    async def test_degraded_status(self) -> None:
        """一部コネクタが異常な場合はdegradedを返す"""
        app = create_app()
        mock_check = AsyncMock(
            side_effect=[
                {"name": "sap", "status": "healthy", "latency_ms": 10.0, "circuit_breaker": {}},
                {"name": "box", "status": "error", "latency_ms": 5.0, "error": "timeout"},
            ]
        )

        with (
            patch(
                "src.api.routes.connectors.CONNECTOR_CLASSES",
                {"sap": MagicMock, "box": MagicMock},
            ),
            patch("src.api.routes.connectors._check_single_connector", mock_check),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/connectors/health")

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "degraded"
            assert data["healthy"] == 1

    async def test_all_unhealthy(self) -> None:
        """全コネクタが異常な場合はunhealthyを返す"""
        app = create_app()
        mock_check = AsyncMock(
            return_value={
                "name": "sap",
                "status": "error",
                "latency_ms": 100.0,
                "error": "connection refused",
            }
        )

        with (
            patch(
                "src.api.routes.connectors.CONNECTOR_CLASSES",
                {"sap": MagicMock},
            ),
            patch("src.api.routes.connectors._check_single_connector", mock_check),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/connectors/health")

            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert data["healthy"] == 0


@pytest.mark.unit
class TestConnectorSingleHealthRoute:
    """GET /api/v1/connectors/{name}/health"""

    async def test_known_connector(self) -> None:
        """存在するコネクタの個別ヘルスチェック"""
        app = create_app()
        mock_check = AsyncMock(
            return_value={
                "name": "sap",
                "status": "healthy",
                "latency_ms": 15.0,
                "circuit_breaker": {"state": "closed", "failure_count": 0, "failure_threshold": 5},
            }
        )

        with patch("src.api.routes.connectors._check_single_connector", mock_check):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/connectors/sap/health")

            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "sap"
            assert data["status"] == "healthy"

    async def test_unknown_connector(self) -> None:
        """存在しないコネクタの場合はunknownを返す"""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/connectors/nonexistent/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unknown"
        assert "nonexistent" in data["error"]


@pytest.mark.unit
class TestConnectorsMetricsRoute:
    """GET /api/v1/connectors/metrics"""

    async def test_metrics_endpoint(self) -> None:
        """メトリクスエンドポイントが正常応答"""
        app = create_app()
        mock_connector = _make_mock_connector()

        with patch(
            "src.api.routes.connectors.CONNECTOR_CLASSES",
            {"sap": lambda: mock_connector},
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/connectors/metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert "connectors" in data
        assert "sap" in data["connectors"]

    async def test_metrics_with_error(self) -> None:
        """コネクタ初期化エラー時もエラー情報を返す"""
        app = create_app()

        def _raise() -> None:
            raise RuntimeError("init failed")

        with patch(
            "src.api.routes.connectors.CONNECTOR_CLASSES",
            {"broken": _raise},
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/connectors/metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data["connectors"]["broken"]


@pytest.mark.unit
class TestCheckSingleConnector:
    """_check_single_connector ユニットテスト"""

    async def test_healthy_connector(self) -> None:
        """正常コネクタのチェック結果"""
        from src.api.routes.connectors import _check_single_connector

        mock_instance = _make_mock_connector(healthy=True)

        with (
            patch("src.api.routes.connectors.connector_circuit_breaker_state"),
            patch("src.api.routes.connectors.connector_circuit_breaker_failures"),
        ):
            result = await _check_single_connector("test", lambda: mock_instance)  # type: ignore[arg-type]

        assert result["name"] == "test"
        assert result["status"] == "healthy"
        assert "latency_ms" in result
        assert result["circuit_breaker"]["state"] == "closed"

    async def test_unhealthy_connector(self) -> None:
        """異常コネクタのチェック結果"""
        from src.api.routes.connectors import _check_single_connector

        mock_instance = _make_mock_connector(healthy=False)

        with (
            patch("src.api.routes.connectors.connector_circuit_breaker_state"),
            patch("src.api.routes.connectors.connector_circuit_breaker_failures"),
        ):
            result = await _check_single_connector("test", lambda: mock_instance)  # type: ignore[arg-type]

        assert result["status"] == "unhealthy"

    async def test_exception_handling(self) -> None:
        """例外発生時のチェック結果"""
        from src.api.routes.connectors import _check_single_connector

        def _raise_cls() -> None:
            raise ConnectionError("connection refused")

        result = await _check_single_connector("broken", _raise_cls)  # type: ignore[arg-type]

        assert result["status"] == "error"
        assert "connection refused" in result["error"]
        assert result["circuit_breaker"]["state"] == "unknown"
