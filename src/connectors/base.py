"""コネクタ基底クラス — リトライ + サーキットブレーカー共通基盤"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import httpx
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

F = TypeVar("F", bound=Callable[..., Any])

# リトライ対象の例外
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    TimeoutError,
    ConnectionError,
    OSError,
)

# リトライデコレータ（コネクタ共通）
connector_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)


class CircuitBreaker:
    """シンプルなサーキットブレーカー

    連続失敗が閾値を超えるとオープン状態になり、
    クールダウン期間中はリクエストを即座に拒否する。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """サーキットがオープン（遮断中）かどうか"""
        if not self._is_open:
            return False
        # クールダウン経過でハーフオープンに遷移
        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self._cooldown_seconds:
            self._is_open = False
            self._failure_count = 0
            return False
        return True

    def record_success(self) -> None:
        """成功を記録 → カウンタリセット"""
        self._failure_count = 0
        self._is_open = False

    def record_failure(self) -> None:
        """失敗を記録 → 閾値超過でオープン"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._is_open = True

    def reset(self) -> None:
        """手動リセット"""
        self._failure_count = 0
        self._is_open = False
        self._last_failure_time = 0.0


class CircuitBreakerOpenError(Exception):
    """サーキットブレーカーがオープン状態"""

    def __init__(self, connector_name: str) -> None:
        super().__init__(f"サーキットブレーカーオープン: {connector_name}")
        self.connector_name = connector_name


def with_circuit_breaker(func: F) -> F:
    """サーキットブレーカーデコレータ（BaseConnector用）"""

    @wraps(func)
    async def wrapper(self: "BaseConnector", *args: Any, **kwargs: Any) -> Any:
        if self.circuit_breaker.is_open:
            logger.warning(
                "{}:{} — サーキットブレーカーオープン、リクエスト拒否",
                self.connector_name,
                func.__name__,
            )
            raise CircuitBreakerOpenError(self.connector_name)
        try:
            result = await func(self, *args, **kwargs)
            self.circuit_breaker.record_success()
            return result
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.warning(
                "{}:{} — 失敗記録 ({}/{}): {}",
                self.connector_name,
                func.__name__,
                self.circuit_breaker._failure_count,
                self.circuit_breaker._failure_threshold,
                str(e),
            )
            raise

    return wrapper  # type: ignore[return-value]


class BaseConnector(ABC):
    """外部システムコネクタの基底クラス"""

    def __init__(self) -> None:
        self.circuit_breaker = CircuitBreaker()

    @property
    @abstractmethod
    def connector_name(self) -> str:
        """コネクタ名"""
        ...

    @abstractmethod
    async def connect(self) -> bool:
        """接続確立"""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """接続切断"""
        ...

    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """データ検索"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """接続チェック"""
        ...
