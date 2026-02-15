"""LLMコストトラッカーテスト"""

import pytest

from src.llm_gateway.cost_tracker import CostRecord, CostTracker
from src.llm_gateway.providers.base import LLMResponse


@pytest.mark.unit
class TestCostRecord:
    """CostRecordデータクラスのテスト"""

    def test_defaults(self) -> None:
        """デフォルト値"""
        record = CostRecord()
        assert record.total_cost_usd == 0.0
        assert record.total_input_tokens == 0
        assert record.total_output_tokens == 0
        assert record.request_count == 0


@pytest.mark.unit
class TestCostTracker:
    """CostTrackerのテスト"""

    def test_empty_summary(self) -> None:
        """空のサマリー"""
        tracker = CostTracker()
        summary = tracker.get_summary()
        assert summary["total_cost_usd"] == 0.0
        assert summary["total_cost_jpy"] == 0.0
        assert summary["total_tokens"] == 0
        assert summary["total_requests"] == 0
        assert summary["by_model"] == {}

    def test_record_single(self) -> None:
        """単一レスポンスの記録"""
        tracker = CostTracker()
        resp = LLMResponse(
            content="test",
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
        )
        tracker.record(resp)

        summary = tracker.get_summary()
        assert summary["total_cost_usd"] == 0.001
        assert summary["total_tokens"] == 150
        assert summary["total_requests"] == 1
        assert "anthropic:claude-sonnet-4-5-20250929" in summary["by_model"]

    def test_record_multiple_same_model(self) -> None:
        """同モデルの複数記録が集約される"""
        tracker = CostTracker()
        for _ in range(3):
            resp = LLMResponse(
                content="",
                model="claude-sonnet-4-5-20250929",
                provider="anthropic",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
            )
            tracker.record(resp)

        summary = tracker.get_summary()
        assert summary["total_requests"] == 3
        assert summary["total_cost_usd"] == pytest.approx(0.003)
        model_info = summary["by_model"]["anthropic:claude-sonnet-4-5-20250929"]
        assert model_info["requests"] == 3

    def test_record_multiple_models(self) -> None:
        """異なるモデルは別キーで記録"""
        tracker = CostTracker()
        tracker.record(
            LLMResponse(
                content="",
                model="sonnet",
                provider="anthropic",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
            )
        )
        tracker.record(
            LLMResponse(
                content="",
                model="gpt-4o",
                provider="azure",
                input_tokens=200,
                output_tokens=100,
                cost_usd=0.005,
            )
        )

        summary = tracker.get_summary()
        assert summary["total_requests"] == 2
        assert len(summary["by_model"]) == 2
        assert "anthropic:sonnet" in summary["by_model"]
        assert "azure:gpt-4o" in summary["by_model"]

    def test_jpy_conversion(self) -> None:
        """JPY換算"""
        tracker = CostTracker()
        tracker.record(LLMResponse(content="", model="m", provider="p", cost_usd=1.0))
        summary = tracker.get_summary()
        assert summary["total_cost_jpy"] == 150.0

    def test_reset(self) -> None:
        """リセット"""
        tracker = CostTracker()
        tracker.record(
            LLMResponse(content="", model="m", provider="p", input_tokens=100, output_tokens=50, cost_usd=0.01)
        )
        tracker.reset()

        summary = tracker.get_summary()
        assert summary["total_cost_usd"] == 0.0
        assert summary["total_requests"] == 0
