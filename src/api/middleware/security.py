"""セキュリティミドルウェア — WAF的防御・入力サニタイズ・セキュリティヘッダー"""

import re
import time
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティレスポンスヘッダーを付与

    OWASP推奨ヘッダーを自動追加:
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Strict-Transport-Security
    - Content-Security-Policy
    - Referrer-Policy
    - Permissions-Policy
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # サーバー情報を隠す
        if "Server" in response.headers:
            del response.headers["Server"]

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """リクエストバリデーション — SQLインジェクション/XSS防御

    パスパラメータとクエリ文字列のパターンチェック。
    """

    # 危険なパターン
    SQL_INJECTION_PATTERNS = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(0x[0-9a-fA-F]+)",
    ]

    XSS_PATTERNS = [
        r"(<script\b[^>]*>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
        r"(<iframe\b[^>]*>)",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"(\.\.\/|\.\.\\)",
        r"(%2e%2e|%252e%252e)",
    ]

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE)
            for patterns in [
                self.SQL_INJECTION_PATTERNS,
                self.XSS_PATTERNS,
                self.PATH_TRAVERSAL_PATTERNS,
            ]
            for p in patterns
        ]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # パスチェック
        path = request.url.path
        if self._is_suspicious(path):
            logger.warning(
                "不審なリクエストパス検出: path={}, ip={}",
                path,
                request.client.host if request.client else "unknown",
            )
            return Response(content="Forbidden", status_code=403)

        # クエリパラメータチェック
        for key, value in request.query_params.items():
            if self._is_suspicious(value):
                logger.warning(
                    "不審なクエリパラメータ検出: key={}, ip={}",
                    key,
                    request.client.host if request.client else "unknown",
                )
                return Response(content="Forbidden", status_code=403)

        return await call_next(request)

    def _is_suspicious(self, value: str) -> bool:
        """危険パターンの検出"""
        return any(pattern.search(value) for pattern in self._compiled_patterns)


class IPThrottleMiddleware(BaseHTTPMiddleware):
    """IP単位の高頻度リクエスト制限

    短時間に大量リクエストを送るIPを一時ブロック。
    DDoS軽減の簡易対策。
    """

    def __init__(
        self,
        app: Any,
        max_requests_per_minute: int = 120,
        block_duration_seconds: int = 300,
    ) -> None:
        super().__init__(app)
        self._max_rpm = max_requests_per_minute
        self._block_duration = block_duration_seconds
        # {ip: [timestamp, ...]}
        self._request_log: dict[str, list[float]] = defaultdict(list)
        # {ip: blocked_until}
        self._blocked: dict[str, float] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "0.0.0.0"
        now = time.time()

        # ブロックチェック
        if client_ip in self._blocked:
            if now < self._blocked[client_ip]:
                return Response(
                    content="Too Many Requests",
                    status_code=429,
                    headers={"Retry-After": str(self._block_duration)},
                )
            else:
                del self._blocked[client_ip]

        # リクエストログ更新
        window_start = now - 60  # 直近1分
        self._request_log[client_ip] = [t for t in self._request_log[client_ip] if t > window_start]
        self._request_log[client_ip].append(now)

        if len(self._request_log[client_ip]) > self._max_rpm:
            self._blocked[client_ip] = now + self._block_duration
            logger.warning(
                "IPブロック: ip={}, requests_in_minute={}",
                client_ip,
                len(self._request_log[client_ip]),
            )
            return Response(
                content="Too Many Requests",
                status_code=429,
                headers={"Retry-After": str(self._block_duration)},
            )

        return await call_next(request)
