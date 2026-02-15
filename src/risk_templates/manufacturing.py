"""製造業リスクテンプレート

製造業特有のリスク項目（在庫管理、品質管理、サプライチェーン等）
およびJ-SOX対応の統制手続きを定義。
"""

from src.risk_templates import (
    ControlItem,
    IndustryTemplateDefinition,
    RiskItem,
)

_MANUFACTURING_RISKS: list[RiskItem] = [
    # ── 在庫管理 ──
    RiskItem(
        risk_code="MFG-001",
        risk_name="棚卸資産の評価誤り",
        category="financial_process",
        subcategory="inventory_valuation",
        description="棚卸資産の原価計算・低価法適用の誤りリスク。滞留在庫の評価減漏れ。",
        default_likelihood=4,
        default_impact=4,
        regulatory_ref="J-SOX 実施基準 II.2.(2)",
        applicable_assertions=["評価", "存在性"],
        tags=["j-sox", "inventory", "valuation"],
    ),
    RiskItem(
        risk_code="MFG-002",
        risk_name="在庫実査と帳簿の乖離",
        category="financial_process",
        subcategory="inventory_count",
        description="実地棚卸と帳簿在庫の差異。入出庫処理の遅延・漏れ。",
        default_likelihood=3,
        default_impact=3,
        regulatory_ref="J-SOX 実施基準 II.2.(1)",
        applicable_assertions=["存在性", "完全性"],
        tags=["j-sox", "inventory", "physical_count"],
    ),
    # ── 原価計算 ──
    RiskItem(
        risk_code="MFG-003",
        risk_name="製造原価の配賦誤り",
        category="financial_process",
        subcategory="cost_allocation",
        description="間接費の配賦基準誤り。原価計算システムのマスタ設定不備。",
        default_likelihood=3,
        default_impact=4,
        regulatory_ref="J-SOX 実施基準 II.2.(2)",
        applicable_assertions=["評価", "完全性"],
        tags=["j-sox", "cost", "allocation"],
    ),
    # ── 品質管理 ──
    RiskItem(
        risk_code="MFG-004",
        risk_name="品質データ改ざん",
        category="compliance",
        subcategory="quality_assurance",
        description="検査データの改ざん・不正リスク。品質管理体制の不備。",
        default_likelihood=2,
        default_impact=5,
        regulatory_ref="品質管理基準",
        applicable_assertions=["存在性"],
        tags=["quality", "compliance", "fraud"],
    ),
    RiskItem(
        risk_code="MFG-005",
        risk_name="製品リコール対応の遅延",
        category="compliance",
        subcategory="product_safety",
        description="品質問題検出時のリコール判断・実行の遅延リスク。",
        default_likelihood=2,
        default_impact=5,
        regulatory_ref="製造物責任法",
        applicable_assertions=["完全性"],
        tags=["quality", "recall", "compliance"],
    ),
    # ── サプライチェーン ──
    RiskItem(
        risk_code="MFG-006",
        risk_name="主要取引先の集中リスク",
        category="financial_process",
        subcategory="supply_chain",
        description="特定仕入先への依存度が高く、供給途絶時の事業継続リスク。",
        default_likelihood=3,
        default_impact=4,
        applicable_assertions=["権利と義務"],
        tags=["supply_chain", "concentration"],
    ),
    # ── アクセス制御 ──
    RiskItem(
        risk_code="MFG-007",
        risk_name="生産管理システムの不正アクセス",
        category="access_control",
        subcategory="erp_access",
        description="ERP（SAP等）の生産・在庫モジュールへのアクセス権限管理不備。",
        default_likelihood=3,
        default_impact=4,
        regulatory_ref="J-SOX IT統制基準 3.1",
        applicable_assertions=["存在性", "権利と義務"],
        tags=["j-sox", "it_gc", "access"],
    ),
    # ── IT全般統制 ──
    RiskItem(
        risk_code="MFG-008",
        risk_name="生産システム変更管理の不備",
        category="it_general",
        subcategory="change_management",
        description="MES/ERPシステムの変更承認・テスト・本番移行プロセスの不備。",
        default_likelihood=3,
        default_impact=4,
        regulatory_ref="J-SOX IT統制基準 4.1",
        applicable_assertions=["存在性", "完全性"],
        tags=["j-sox", "it_gc", "change_mgmt"],
    ),
]

_MANUFACTURING_CONTROLS: list[ControlItem] = [
    # 在庫管理
    ControlItem(
        control_code="MC-001",
        control_name="月次在庫循環棚卸",
        risk_code="MFG-001",
        control_type="detective",
        frequency="monthly",
        test_approach="observation",
        recommended_sample_size=0,
        description="ABC分析に基づく月次循環棚卸の実施と差異調査。",
    ),
    ControlItem(
        control_code="MC-002",
        control_name="滞留在庫レビュー",
        risk_code="MFG-001",
        control_type="detective",
        frequency="quarterly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="一定期間以上滞留在庫の評価減判定レビュー。",
    ),
    ControlItem(
        control_code="MC-003",
        control_name="入出庫伝票照合",
        risk_code="MFG-002",
        control_type="detective",
        frequency="daily",
        test_approach="inspection",
        recommended_sample_size=25,
        description="入出庫伝票と実物の照合確認。受払記録の正確性検証。",
    ),
    # 原価計算
    ControlItem(
        control_code="MC-004",
        control_name="原価差異分析レビュー",
        risk_code="MFG-003",
        control_type="detective",
        frequency="monthly",
        test_approach="reperformance",
        recommended_sample_size=0,
        description="標準原価と実際原価の差異分析。異常差異の原因調査。",
    ),
    # 品質管理
    ControlItem(
        control_code="MC-005",
        control_name="品質検査記録クロスチェック",
        risk_code="MFG-004",
        control_type="detective",
        frequency="weekly",
        test_approach="inspection",
        recommended_sample_size=25,
        description="品質検査データと出荷記録のクロスチェック。",
    ),
    # サプライチェーン
    ControlItem(
        control_code="MC-006",
        control_name="取引先集中度モニタリング",
        risk_code="MFG-006",
        control_type="detective",
        frequency="quarterly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="上位10社の取引額集中度分析と代替先評価。",
    ),
    # アクセス制御
    ControlItem(
        control_code="MC-007",
        control_name="ERPアクセス権限棚卸",
        risk_code="MFG-007",
        control_type="detective",
        frequency="quarterly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="生産・在庫モジュールのアクセス権限棚卸とレビュー。",
        automation_level="semi_auto",
    ),
    # IT統制
    ControlItem(
        control_code="MC-008",
        control_name="変更管理承認プロセス",
        risk_code="MFG-008",
        control_type="preventive",
        frequency="daily",
        test_approach="inspection",
        recommended_sample_size=25,
        description="MES/ERPシステム変更の承認フローとテスト記録確認。",
    ),
]


def get_manufacturing_template() -> IndustryTemplateDefinition:
    """製造業テンプレートを生成"""
    return IndustryTemplateDefinition(
        industry_code="manufacturing",
        industry_name="製造業",
        region="JP",
        version="1.0",
        description="製造業向けリスク・統制テンプレート。"
        "在庫管理・原価計算・品質管理・サプライチェーンに特化。",
        regulatory_framework="J-SOX",
        risks=_MANUFACTURING_RISKS,
        controls=_MANUFACTURING_CONTROLS,
    )
