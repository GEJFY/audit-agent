"""製造業リスクテンプレートのテスト"""

import pytest

from src.risk_templates.manufacturing import get_manufacturing_template


@pytest.mark.unit
class TestManufacturingTemplate:
    """製造業テンプレートのテスト"""

    def test_template_metadata(self) -> None:
        tmpl = get_manufacturing_template()
        assert tmpl.industry_code == "manufacturing"
        assert tmpl.industry_name == "製造業"
        assert tmpl.region == "JP"
        assert tmpl.regulatory_framework == "J-SOX"

    def test_risk_count(self) -> None:
        tmpl = get_manufacturing_template()
        assert tmpl.risk_count == 8

    def test_control_count(self) -> None:
        tmpl = get_manufacturing_template()
        assert tmpl.control_count == 8

    def test_risk_codes_unique(self) -> None:
        tmpl = get_manufacturing_template()
        codes = [r.risk_code for r in tmpl.risks]
        assert len(codes) == len(set(codes))

    def test_control_codes_unique(self) -> None:
        tmpl = get_manufacturing_template()
        codes = [c.control_code for c in tmpl.controls]
        assert len(codes) == len(set(codes))

    def test_all_controls_reference_valid_risk(self) -> None:
        tmpl = get_manufacturing_template()
        risk_codes = {r.risk_code for r in tmpl.risks}
        for ctrl in tmpl.controls:
            assert ctrl.risk_code in risk_codes, f"{ctrl.control_code} references unknown risk {ctrl.risk_code}"

    def test_inventory_risks(self) -> None:
        """在庫管理リスクが含まれること"""
        tmpl = get_manufacturing_template()
        inv_risks = [r for r in tmpl.risks if "inventory" in r.tags]
        assert len(inv_risks) >= 2

    def test_quality_risks(self) -> None:
        """品質管理リスクが含まれること"""
        tmpl = get_manufacturing_template()
        quality_risks = [r for r in tmpl.risks if "quality" in r.tags]
        assert len(quality_risks) >= 1

    def test_supply_chain_risks(self) -> None:
        """サプライチェーンリスクが含まれること"""
        tmpl = get_manufacturing_template()
        sc_risks = [r for r in tmpl.risks if "supply_chain" in r.tags]
        assert len(sc_risks) >= 1

    def test_categories_coverage(self) -> None:
        tmpl = get_manufacturing_template()
        cats = tmpl.get_categories()
        assert len(cats) >= 3
        assert "financial_process" in cats
