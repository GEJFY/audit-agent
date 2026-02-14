"""相関IDミドルウェア — リクエスト追跡"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.monitoring.logging import correlation_id_var, tenant_id_var


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """各リクエストに一意の相関IDを付与"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 相関ID: ヘッダーから取得 or 新規生成
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_var.set(correlation_id)

        # テナントID: JWTから取得（認証後に設定）
        tenant_id = request.headers.get("X-Tenant-ID", "")
        if tenant_id:
            tenant_id_var.set(tenant_id)

        response = await call_next(request)

        # レスポンスヘッダーに相関IDを付与
        response.headers["X-Correlation-ID"] = correlation_id

        return response
