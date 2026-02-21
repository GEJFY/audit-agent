"""コネクタヘルスチェック + メトリクス API"""

import time
from typing import Any

from fastapi import APIRouter
from loguru import logger

from src.connectors import (
    BoxConnector,
    EmailConnector,
    SAPConnector,
    SharePointConnector,
)
from src.connectors.base import BaseConnector
from src.monitoring.metrics import (
    connector_circuit_breaker_failures,
    connector_circuit_breaker_state,
)

router = APIRouter()

# コネクタ名 → クラスのマッピング
CONNECTOR_CLASSES: dict[str, type[BaseConnector]] = {
    "sap": SAPConnector,
    "sharepoint": SharePointConnector,
    "box": BoxConnector,
    "email": EmailConnector,
}


async def _check_single_connector(name: str, cls: type[BaseConnector]) -> dict[str, Any]:
    """単一コネクタのヘルスチェックを実行"""
    start = time.monotonic()
    try:
        connector = cls()
        healthy = await connector.health_check()
        latency_ms = (time.monotonic() - start) * 1000

        # CB状態をPrometheusに公開
        connector_circuit_breaker_state.labels(connector=name).set(1 if connector.circuit_breaker.is_open else 0)
        connector_circuit_breaker_failures.labels(connector=name).set(connector.circuit_breaker._failure_count)

        return {
            "name": name,
            "status": "healthy" if healthy else "unhealthy",
            "latency_ms": round(latency_ms, 2),
            "circuit_breaker": {
                "state": "open" if connector.circuit_breaker.is_open else "closed",
                "failure_count": connector.circuit_breaker._failure_count,
                "failure_threshold": connector.circuit_breaker._failure_threshold,
            },
        }
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        logger.warning("コネクタヘルスチェック失敗: {} — {}", name, str(e))
        return {
            "name": name,
            "status": "error",
            "latency_ms": round(latency_ms, 2),
            "error": str(e),
            "circuit_breaker": {"state": "unknown", "failure_count": 0, "failure_threshold": 5},
        }


@router.get("/health")
async def connectors_health() -> dict[str, Any]:
    """全コネクタのヘルスチェック"""
    results = []
    for name, cls in CONNECTOR_CLASSES.items():
        result = await _check_single_connector(name, cls)
        results.append(result)

    healthy_count = sum(1 for r in results if r["status"] == "healthy")
    total = len(results)

    if healthy_count == total:
        overall = "healthy"
    elif healthy_count > 0:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "total": total,
        "healthy": healthy_count,
        "connectors": results,
    }


@router.get("/{connector_name}/health")
async def connector_health(connector_name: str) -> dict[str, Any]:
    """個別コネクタのヘルスチェック"""
    cls = CONNECTOR_CLASSES.get(connector_name)
    if cls is None:
        return {
            "name": connector_name,
            "status": "unknown",
            "error": f"Unknown connector: {connector_name}. Available: {list(CONNECTOR_CLASSES.keys())}",
        }
    return await _check_single_connector(connector_name, cls)


@router.get("/metrics")
async def connectors_metrics() -> dict[str, Any]:
    """全コネクタのメトリクスサマリー"""
    metrics: dict[str, Any] = {}
    for name, cls in CONNECTOR_CLASSES.items():
        try:
            connector = cls()
            cb = connector.circuit_breaker
            metrics[name] = {
                "circuit_breaker": {
                    "state": "open" if cb.is_open else "closed",
                    "failure_count": cb._failure_count,
                    "failure_threshold": cb._failure_threshold,
                    "cooldown_seconds": cb._cooldown_seconds,
                },
            }
        except Exception as e:
            metrics[name] = {"error": str(e)}

    return {"connectors": metrics}
