"""コネクタ基底クラス"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class BaseConnector(ABC):
    """外部システムコネクタの基底クラス"""

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
