"""SLA監視テスト"""

import pytest

from src.monitoring.sla import (
    SLAMetricType,
    SLAMonitor,
    SLARecord,
    SLATarget,
)


@pytest.mark.unit
class TestSLAMetricType:
    """SLAメトリクス種別テスト"""

    def test_values(self) -> None:
        assert SLAMetricType.API_RESPONSE_TIME == "api_response_time"
        assert SLAMetricType.LLM_LATENCY == "llm_latency"
        assert SLAMetricType.UPTIME == "uptime"


@pytest.mark.unit
class TestSLATarget:
    """SLA目標テスト"""

    def test_defaults(self) -> None:
        target = SLATarget(metric=SLAMetricType.API_RESPONSE_TIME, threshold_ms=500)
        assert target.threshold_percent == 99.9
        assert target.evaluation_window_hours == 24


@pytest.mark.unit
class TestSLARecord:
    """SLAレコードテスト"""

    def test_create(self) -> None:
        record = SLARecord(
            metric=SLAMetricType.API_RESPONSE_TIME,
            value=250.0,
            tenant_id="t-001",
        )
        assert record.value == 250.0
        assert record.tenant_id == "t-001"
        assert record.timestamp > 0


@pytest.mark.unit
class TestSLAMonitor:
    """SLAMonitorテスト"""

    def test_record_metric(self) -> None:
        """メトリクス記録"""
        monitor = SLAMonitor()
        record = SLARecord(
            metric=SLAMetricType.API_RESPONSE_TIME,
            value=200.0,
            tenant_id="t-001",
        )
        monitor.record_metric(record)
        assert len(monitor._records["t-001:api_response_time"]) == 1

    def test_get_targets_enterprise(self) -> None:
        """Enterprise Tier目標"""
        monitor = SLAMonitor()
        targets = monitor.get_targets("enterprise")
        assert len(targets) == 3
        api_target = next(t for t in targets if t.metric == SLAMetricType.API_RESPONSE_TIME)
        assert api_target.threshold_ms == 500

    def test_get_targets_unknown_tier(self) -> None:
        """未知のTierはstarterにフォールバック"""
        monitor = SLAMonitor()
        targets = monitor.get_targets("unknown")
        starter_targets = monitor.get_targets("starter")
        assert targets == starter_targets

    def test_evaluate_no_violations(self) -> None:
        """違反なし"""
        monitor = SLAMonitor()
        for _ in range(5):
            monitor.record_metric(
                SLARecord(
                    metric=SLAMetricType.API_RESPONSE_TIME,
                    value=100.0,
                    tenant_id="t-001",
                )
            )

        violations = monitor.evaluate("t-001", tier="enterprise")
        assert len(violations) == 0

    def test_evaluate_latency_violation(self) -> None:
        """レイテンシ違反"""
        monitor = SLAMonitor()
        for _ in range(5):
            monitor.record_metric(
                SLARecord(
                    metric=SLAMetricType.API_RESPONSE_TIME,
                    value=800.0,
                    tenant_id="t-001",
                )
            )

        violations = monitor.evaluate("t-001", tier="enterprise")
        assert len(violations) >= 1
        api_violation = next(v for v in violations if v.metric == SLAMetricType.API_RESPONSE_TIME)
        assert api_violation.severity == "warning"

    def test_evaluate_critical_violation(self) -> None:
        """重大レイテンシ違反（閾値の2倍超）"""
        monitor = SLAMonitor()
        for _ in range(5):
            monitor.record_metric(
                SLARecord(
                    metric=SLAMetricType.API_RESPONSE_TIME,
                    value=1500.0,  # 500ms * 2 = 1000ms超
                    tenant_id="t-001",
                )
            )

        violations = monitor.evaluate("t-001", tier="enterprise")
        api_violation = next(v for v in violations if v.metric == SLAMetricType.API_RESPONSE_TIME)
        assert api_violation.severity == "critical"

    def test_evaluate_uptime_violation(self) -> None:
        """可用性違反"""
        monitor = SLAMonitor()
        for _ in range(5):
            monitor.record_metric(
                SLARecord(
                    metric=SLAMetricType.UPTIME,
                    value=98.0,  # enterprise目標: 99.9%
                    tenant_id="t-001",
                )
            )

        violations = monitor.evaluate("t-001", tier="enterprise")
        uptime_violation = next(v for v in violations if v.metric == SLAMetricType.UPTIME)
        assert uptime_violation.severity == "critical"

    def test_evaluate_no_records(self) -> None:
        """レコードなし→違反なし"""
        monitor = SLAMonitor()
        violations = monitor.evaluate("t-001", tier="enterprise")
        assert violations == []

    def test_get_violations_all(self) -> None:
        """全違反取得"""
        monitor = SLAMonitor()
        for _ in range(3):
            monitor.record_metric(
                SLARecord(
                    metric=SLAMetricType.API_RESPONSE_TIME,
                    value=5000.0,
                    tenant_id="t-001",
                )
            )
        monitor.evaluate("t-001", tier="enterprise")
        assert len(monitor.get_violations()) >= 1

    def test_get_violations_by_tenant(self) -> None:
        """テナント別違反取得"""
        monitor = SLAMonitor()
        for _ in range(3):
            monitor.record_metric(
                SLARecord(
                    metric=SLAMetricType.API_RESPONSE_TIME,
                    value=5000.0,
                    tenant_id="t-001",
                )
            )
        monitor.evaluate("t-001", tier="enterprise")
        assert len(monitor.get_violations("t-001")) >= 1
        assert len(monitor.get_violations("t-002")) == 0

    def test_get_summary(self) -> None:
        """SLAサマリー"""
        monitor = SLAMonitor()
        monitor.record_metric(
            SLARecord(
                metric=SLAMetricType.API_RESPONSE_TIME,
                value=200.0,
                tenant_id="t-001",
            )
        )
        monitor.record_metric(
            SLARecord(
                metric=SLAMetricType.API_RESPONSE_TIME,
                value=300.0,
                tenant_id="t-001",
            )
        )

        summary = monitor.get_summary("t-001")
        assert summary["tenant_id"] == "t-001"
        assert summary["total_records"] == 2
        assert "api_response_time" in summary["metrics"]
        assert summary["metrics"]["api_response_time"]["avg"] == 250.0

    def test_reset(self) -> None:
        """リセット"""
        monitor = SLAMonitor()
        monitor.record_metric(
            SLARecord(
                metric=SLAMetricType.API_RESPONSE_TIME,
                value=200.0,
                tenant_id="t-001",
            )
        )
        monitor.reset()
        assert monitor._records == {}
        assert monitor._violations == []
