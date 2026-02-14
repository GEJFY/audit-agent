"""LLMプロバイダー基底クラス"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """LLM応答の統一型"""

    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_cost_jpy(self) -> float:
        """JPY換算（概算: 1USD=150JPY）"""
        return self.cost_usd * 150


class BaseLLMProvider(ABC):
    """LLMプロバイダー基底クラス"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダー名"""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMResponse:
        """テキスト生成"""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """構造化データ生成（JSONスキーマ指定）"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """接続チェック"""
        ...
