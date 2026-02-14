"""Prometheus Metrics テスト"""

import pytest

from src.monitoring.metrics import (
    app_info,
    http_requests_total,
    http_request_duration_seconds,
    agent_executions_total,
    agent_execution_duration_seconds,
    agent_confidence_score,
    llm_requests_total,
    llm_tokens_total,
    llm_cost_total,
    dialogue_messages_total,
    escalations_total,
    db_pool_size,
)


@pytest.mark.unit
class TestPrometheusMetrics:
    """Prometheusメトリクスの定義テスト"""

    def test_app_info_exists(self) -> None:
        """アプリ情報メトリクスが存在"""
        assert app_info is not None

    def test_http_metrics(self) -> None:
        """HTTPメトリクスが正常にインクリメント可能"""
        http_requests_total.labels(
            method="GET",
            endpoint="/api/v1/health",
            status_code="200",
        ).inc()

        http_request_duration_seconds.labels(
            method="GET",
            endpoint="/api/v1/health",
        ).observe(0.05)

    def test_agent_metrics(self) -> None:
        """Agentメトリクスが正常に記録可能"""
        agent_executions_total.labels(
            agent_type="auditor_anomaly_detective",
            status="success",
        ).inc()

        agent_execution_duration_seconds.labels(
            agent_type="auditor_anomaly_detective",
        ).observe(5.0)

        agent_confidence_score.labels(
            agent_type="auditor_anomaly_detective",
        ).observe(0.85)

    def test_llm_metrics(self) -> None:
        """LLMメトリクスが正常に記録可能"""
        llm_requests_total.labels(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            status="success",
        ).inc()

        llm_tokens_total.labels(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            direction="input",
        ).inc(100)

        llm_cost_total.labels(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
        ).inc(0.001)

    def test_dialogue_metrics(self) -> None:
        """対話メトリクスが正常に記録可能"""
        dialogue_messages_total.labels(
            message_type="question",
            direction="auditor_to_auditee",
        ).inc()

        escalations_total.labels(
            reason="low_confidence",
            severity="medium",
        ).inc()

    def test_db_metrics(self) -> None:
        """DBメトリクスが正常に設定可能"""
        db_pool_size.labels(pool_name="default").set(10)
