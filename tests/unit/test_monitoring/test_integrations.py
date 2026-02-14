"""Monitoring Integrations テスト"""

import pytest
from unittest.mock import patch, MagicMock

from src.monitoring.integrations import (
    setup_sentry,
    setup_datadog,
    setup_langsmith,
    setup_all_integrations,
    DatadogMetrics,
    LangSmithTracer,
    _get_version,
)


@pytest.mark.unit
class TestSetupIntegrations:
    """外部監視統合セットアップのテスト"""

    def test_setup_sentry_no_dsn(self) -> None:
        """DSN未設定でSentryスキップ"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(sentry_dsn="")
            # エラーなく完了
            setup_sentry()

    def test_setup_datadog_no_key(self) -> None:
        """API Key未設定でDatadogスキップ"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(datadog_api_key="")
            setup_datadog()

    def test_setup_langsmith_no_key(self) -> None:
        """API Key未設定でLangSmithスキップ"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(langchain_api_key="")
            setup_langsmith()

    def test_setup_all_integrations(self) -> None:
        """全統合初期化"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sentry_dsn="",
                datadog_api_key="",
                langchain_api_key="",
            )
            # エラーなく完了
            setup_all_integrations()


@pytest.mark.unit
class TestDatadogMetrics:
    """Datadogカスタムメトリクスのテスト"""

    def test_init(self) -> None:
        """初期化テスト"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            metrics = DatadogMetrics()
            assert metrics._statsd is None

    def test_increment_without_statsd(self) -> None:
        """StatsDなしのインクリメント（no-op）"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            metrics = DatadogMetrics()
            # エラーなしで実行完了
            metrics.increment("test.counter")

    def test_gauge_without_statsd(self) -> None:
        """StatsDなしのゲージ設定（no-op）"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            metrics = DatadogMetrics()
            metrics.gauge("test.gauge", 42.0)

    def test_histogram_without_statsd(self) -> None:
        """StatsDなしのヒストグラム（no-op）"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            metrics = DatadogMetrics()
            metrics.histogram("test.histogram", 1.5)

    def test_timing_without_statsd(self) -> None:
        """StatsDなしのタイミング（no-op）"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            metrics = DatadogMetrics()
            metrics.timing("test.timing", 500.0)


@pytest.mark.unit
class TestLangSmithTracer:
    """LangSmithトレーサーのテスト"""

    def test_disabled_when_no_key(self) -> None:
        """API Key未設定で無効"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(langchain_api_key="")
            tracer = LangSmithTracer()
            assert tracer._enabled is False

    def test_enabled_with_key(self) -> None:
        """API Key設定で有効"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(langchain_api_key="ls-test-key")
            tracer = LangSmithTracer()
            assert tracer._enabled is True

    def test_trace_agent_disabled(self) -> None:
        """無効時のトレースはno-op"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(langchain_api_key="")
            tracer = LangSmithTracer()
            # エラーなしで完了
            tracer.trace_agent_execution(
                agent_name="test_agent",
                input_data={"q": "test"},
                output_data={"a": "result"},
            )

    def test_trace_llm_disabled(self) -> None:
        """無効時のLLMトレースはno-op"""
        with patch("src.monitoring.integrations.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(langchain_api_key="")
            tracer = LangSmithTracer()
            tracer.trace_llm_call(
                model="claude-sonnet",
                prompt="test",
                response="result",
                tokens_used=100,
            )


@pytest.mark.unit
class TestGetVersion:
    """バージョン取得のテスト"""

    def test_get_version(self) -> None:
        """バージョン取得"""
        version = _get_version()
        assert isinstance(version, str)
        assert version != ""
