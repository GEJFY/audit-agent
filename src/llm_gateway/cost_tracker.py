"""LLMコスト追跡"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.llm_gateway.providers.base import LLMResponse


@dataclass
class CostRecord:
    """コスト記録"""

    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    request_count: int = 0


class CostTracker:
    """LLM APIコスト追跡"""

    def __init__(self) -> None:
        self._records: dict[str, CostRecord] = defaultdict(CostRecord)

    def record(self, response: LLMResponse) -> None:
        """LLM応答のコストを記録"""
        key = f"{response.provider}:{response.model}"
        record = self._records[key]
        record.total_cost_usd += response.cost_usd
        record.total_input_tokens += response.input_tokens
        record.total_output_tokens += response.output_tokens
        record.request_count += 1

    def get_summary(self) -> dict[str, Any]:
        """コストサマリー"""
        total_cost = sum(r.total_cost_usd for r in self._records.values())
        total_tokens = sum(
            r.total_input_tokens + r.total_output_tokens for r in self._records.values()
        )

        return {
            "total_cost_usd": round(total_cost, 6),
            "total_cost_jpy": round(total_cost * 150, 2),
            "total_tokens": total_tokens,
            "total_requests": sum(r.request_count for r in self._records.values()),
            "by_model": {
                key: {
                    "cost_usd": round(r.total_cost_usd, 6),
                    "input_tokens": r.total_input_tokens,
                    "output_tokens": r.total_output_tokens,
                    "requests": r.request_count,
                }
                for key, r in self._records.items()
            },
        }

    def reset(self) -> None:
        """トラッカーをリセット"""
        self._records.clear()
