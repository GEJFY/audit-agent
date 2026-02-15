"""IT業リスクテンプレートのテスト"""

import pytest

from src.risk_templates.it_services import get_it_services_template


@pytest.mark.unit
class TestITServicesTemplate:
    """IT業テンプレートのテスト"""

    def test_template_metadata(self) -> None:
        tmpl = get_it_services_template()
        assert tmpl.industry_code == "it_services"
        assert tmpl.industry_name == "IT・SaaS"
        assert tmpl.region == "JP"
        assert "ISO 27001" in tmpl.regulatory_framework

    def test_risk_count(self) -> None:
        tmpl = get_it_services_template()
        assert tmpl.risk_count == 10

    def test_control_count(self) -> None:
        tmpl = get_it_services_template()
        assert tmpl.control_count == 9

    def test_risk_codes_unique(self) -> None:
        tmpl = get_it_services_template()
        codes = [r.risk_code for r in tmpl.risks]
        assert len(codes) == len(set(codes))

    def test_control_codes_unique(self) -> None:
        tmpl = get_it_services_template()
        codes = [c.control_code for c in tmpl.controls]
        assert len(codes) == len(set(codes))

    def test_all_controls_reference_valid_risk(self) -> None:
        tmpl = get_it_services_template()
        risk_codes = {r.risk_code for r in tmpl.risks}
        for ctrl in tmpl.controls:
            assert ctrl.risk_code in risk_codes, f"{ctrl.control_code} references unknown risk {ctrl.risk_code}"

    def test_cloud_security_risks(self) -> None:
        """クラウドセキュリティリスクが含まれること"""
        tmpl = get_it_services_template()
        cloud_risks = [r for r in tmpl.risks if "cloud" in r.tags]
        assert len(cloud_risks) >= 1

    def test_sdlc_risks(self) -> None:
        """開発管理リスクが含まれること"""
        tmpl = get_it_services_template()
        sdlc_risks = [r for r in tmpl.risks if "sdlc" in r.tags]
        assert len(sdlc_risks) >= 2

    def test_saas_revenue_risks(self) -> None:
        """SaaS収益リスクが含まれること"""
        tmpl = get_it_services_template()
        saas_risks = [r for r in tmpl.risks if "saas" in r.tags]
        assert len(saas_risks) >= 1

    def test_has_automated_controls(self) -> None:
        """自動化統制が含まれること"""
        tmpl = get_it_services_template()
        auto_controls = [c for c in tmpl.controls if c.automation_level == "full_auto"]
        assert len(auto_controls) >= 2

    def test_categories_coverage(self) -> None:
        tmpl = get_it_services_template()
        cats = tmpl.get_categories()
        assert len(cats) >= 3
        assert "access_control" in cats
        assert "it_general" in cats
