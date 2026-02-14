"""ヘルスチェックエンドポイント"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src import __version__
from src.monitoring.health import HealthChecker, HealthStatus

router = APIRouter()
_checker = HealthChecker()


@router.get("/health")
async def health_check() -> JSONResponse:
    """基本ヘルスチェック"""
    result = await _checker.check_all()

    status_code = 200 if result.status == HealthStatus.HEALTHY else 503

    return JSONResponse(
        status_code=status_code,
        content=result.to_dict(),
    )


@router.get("/health/ready")
async def readiness_check() -> JSONResponse:
    """Readinessプローブ — 依存サービスの準備状態"""
    result = await _checker.check_all()

    status_code = 200 if result.status != HealthStatus.UNHEALTHY else 503

    return JSONResponse(
        status_code=status_code,
        content=result.to_dict(),
    )


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """Livenessプローブ — アプリケーション生存確認"""
    return {"status": "alive", "version": __version__}
