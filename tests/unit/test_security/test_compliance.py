"""ComplianceChecker テスト"""

import pytest

from src.security.compliance import (
    ComplianceChecker,
    ComplianceCheckResult,
    ComplianceFramework,
    ComplianceStatus,
)


@pytest.fixture
def checker() -> ComplianceChecker:
    return ComplianceChecker()


@pytest.fixture
def full_compliance_data() -> dict:
    """全項目準拠データ"""
    return {
        "access_control_enabled": True,
        "monitoring_enabled": True,
        "change_management_enabled": True,
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "audit_trail_enabled": True,
        "data_residency_compliance": True,
        "processing_records": True,
        "dpia_completed": True,
        "data_deletion_capability": True,
        "consent_management": True,
        "data_protection_policy": True,
        "breach_notification_process": True,
        "data_localization": True,
        "cross_border_assessment": True,
        "dpo_appointed": True,
        "region": "JP",
    }


@pytest.mark.unit
class TestComplianceChecker:
    """コンプライアンスチェッカーのテスト"""

    # ── フレームワーク選定 ──────────────────────────────

    def test_get_frameworks_jp(self, checker: ComplianceChecker) -> None:
        """日本リージョンのフレームワーク"""
        frameworks = checker.get_applicable_frameworks("JP")
        assert ComplianceFramework.JSOX in frameworks
        assert ComplianceFramework.SOC2 in frameworks
        assert ComplianceFramework.ISO27001 in frameworks

    def test_get_frameworks_sg(self, checker: ComplianceChecker) -> None:
        """シンガポールリージョンのフレームワーク"""
        frameworks = checker.get_applicable_frameworks("SG")
        assert ComplianceFramework.PDPA in frameworks

    def test_get_frameworks_eu(self, checker: ComplianceChecker) -> None:
        """EUリージョンのフレームワーク"""
        frameworks = checker.get_applicable_frameworks("EU")
        assert ComplianceFramework.GDPR in frameworks

    def test_get_frameworks_cn(self, checker: ComplianceChecker) -> None:
        """中国リージョンのフレームワーク"""
        frameworks = checker.get_applicable_frameworks("CN")
        assert ComplianceFramework.PIPL in frameworks

    def test_get_frameworks_unknown(self, checker: ComplianceChecker) -> None:
        """未知リージョンのデフォルト"""
        frameworks = checker.get_applicable_frameworks("XX")
        assert ComplianceFramework.SOC2 in frameworks

    def test_get_frameworks_case_insensitive(self, checker: ComplianceChecker) -> None:
        """小文字でも動作"""
        frameworks = checker.get_applicable_frameworks("jp")
        assert ComplianceFramework.JSOX in frameworks

    # ── SOC2 チェック ─────────────────────────────────

    def test_soc2_full_compliance(self, checker: ComplianceChecker, full_compliance_data: dict) -> None:
        """SOC2全項目準拠"""
        result = checker.check_soc2(full_compliance_data)
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.score == 100.0
        assert result.finding_count == 0

    def test_soc2_no_data(self, checker: ComplianceChecker) -> None:
        """SOC2データなし — 全所見"""
        result = checker.check_soc2()
        assert result.status == ComplianceStatus.NON_COMPLIANT
        assert result.finding_count > 0
        assert result.high_severity_count > 0

    def test_soc2_partial(self, checker: ComplianceChecker) -> None:
        """SOC2一部準拠"""
        data = {"access_control_enabled": True, "encryption_at_rest": True}
        result = checker.check_soc2(data)
        assert result.status == ComplianceStatus.PARTIAL
        assert 0 < result.score < 100

    def test_soc2_result_properties(self, checker: ComplianceChecker) -> None:
        """SOC2結果プロパティ"""
        result = checker.check_soc2()
        assert isinstance(result, ComplianceCheckResult)
        assert result.framework == "SOC2"
        assert result.checked_at != ""
        assert result.finding_count == len(result.findings)

    # ── ISO 27001 チェック ────────────────────────────

    def test_iso27001_full_compliance(self, checker: ComplianceChecker, full_compliance_data: dict) -> None:
        """ISO27001全項目準拠"""
        result = checker.check_iso27001(full_compliance_data)
        assert result.status == ComplianceStatus.COMPLIANT
        assert result.score == 100.0

    def test_iso27001_no_data(self, checker: ComplianceChecker) -> None:
        """ISO27001データなし"""
        result = checker.check_iso27001()
        assert result.finding_count > 0
        assert result.framework == "ISO27001"

    def test_iso27001_data_residency_jp(self, checker: ComplianceChecker) -> None:
        """日本リージョンのデータ居住地チェック"""
        data = {
            "access_control_enabled": True,
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "monitoring_enabled": True,
            "region": "JP",
            # data_residency_compliance 未設定 → 所見
        }
        result = checker.check_iso27001(data)
        findings_ids = [f.control_id for f in result.findings]
        assert "A.18.1" in findings_ids

    # ── GDPR チェック ─────────────────────────────────

    def test_gdpr_full_compliance(self, checker: ComplianceChecker, full_compliance_data: dict) -> None:
        """GDPR全項目準拠"""
        result = checker.check_gdpr(full_compliance_data)
        assert result.status == ComplianceStatus.COMPLIANT

    def test_gdpr_no_data(self, checker: ComplianceChecker) -> None:
        """GDPRデータなし"""
        result = checker.check_gdpr()
        assert result.framework == "GDPR"
        assert result.finding_count >= 3  # Art.30, Art.32, Art.35, Art.17

    # ── PDPA チェック ─────────────────────────────────

    def test_pdpa_full_compliance(self, checker: ComplianceChecker, full_compliance_data: dict) -> None:
        """PDPA全項目準拠"""
        result = checker.check_pdpa(full_compliance_data)
        assert result.status == ComplianceStatus.COMPLIANT

    def test_pdpa_no_data(self, checker: ComplianceChecker) -> None:
        """PDPAデータなし"""
        result = checker.check_pdpa()
        assert result.framework == "PDPA"
        assert result.finding_count >= 2

    # ── PIPL チェック ─────────────────────────────────

    def test_pipl_full_compliance(self, checker: ComplianceChecker, full_compliance_data: dict) -> None:
        """PIPL全項目準拠"""
        result = checker.check_pipl(full_compliance_data)
        assert result.status == ComplianceStatus.COMPLIANT

    def test_pipl_no_data(self, checker: ComplianceChecker) -> None:
        """PIPLデータなし"""
        result = checker.check_pipl()
        assert result.framework == "PIPL"
        assert result.finding_count >= 2
        # データローカライゼーションが最も重い
        assert result.high_severity_count >= 2

    # ── 全フレームワーク一括チェック ───────────────────

    def test_check_all_jp(self, checker: ComplianceChecker) -> None:
        """日本リージョン全チェック"""
        results = checker.check_all_frameworks("JP")
        frameworks = [r.framework for r in results]
        assert "J-SOX" in frameworks
        assert "SOC2" in frameworks
        assert "ISO27001" in frameworks

    def test_check_all_sg(self, checker: ComplianceChecker, full_compliance_data: dict) -> None:
        """シンガポールリージョン全チェック（準拠データ付き）"""
        results = checker.check_all_frameworks("SG", full_compliance_data)
        assert len(results) >= 2
        assert all(r.status == ComplianceStatus.COMPLIANT for r in results)

    def test_check_all_cn(self, checker: ComplianceChecker) -> None:
        """中国リージョン全チェック"""
        results = checker.check_all_frameworks("CN")
        frameworks = [r.framework for r in results]
        assert "PIPL" in frameworks

    # ── ステータス判定 ────────────────────────────────

    def test_score_to_status_compliant(self) -> None:
        assert ComplianceChecker._score_to_status(85.0) == ComplianceStatus.COMPLIANT

    def test_score_to_status_partial(self) -> None:
        assert ComplianceChecker._score_to_status(65.0) == ComplianceStatus.PARTIAL

    def test_score_to_status_non_compliant(self) -> None:
        assert ComplianceChecker._score_to_status(30.0) == ComplianceStatus.NON_COMPLIANT
