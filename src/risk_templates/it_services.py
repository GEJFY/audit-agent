"""IT業リスクテンプレート

SaaS/クラウド事業者、システム開発会社向けの
リスク項目・統制テンプレート。情報セキュリティ・開発管理中心。
"""

from src.risk_templates import (
    ControlItem,
    IndustryTemplateDefinition,
    RiskItem,
)

_IT_RISKS: list[RiskItem] = [
    # ── 情報セキュリティ ──
    RiskItem(
        risk_code="IT-001",
        risk_name="クラウド環境のセキュリティ設定不備",
        category="access_control",
        subcategory="cloud_security",
        description="AWS/Azure/GCPのセキュリティグループ・IAM設定の不備。",
        default_likelihood=4,
        default_impact=5,
        regulatory_ref="ISO 27001 A.13",
        applicable_assertions=["権利と義務"],
        tags=["cloud", "security", "iam"],
    ),
    RiskItem(
        risk_code="IT-002",
        risk_name="顧客データの漏洩",
        category="compliance",
        subcategory="data_protection",
        description="SaaSプラットフォーム上の顧客データの不正アクセス・漏洩。",
        default_likelihood=3,
        default_impact=5,
        regulatory_ref="個人情報保護法, GDPR",
        applicable_assertions=["権利と義務", "完全性"],
        tags=["privacy", "data_breach", "compliance"],
    ),
    RiskItem(
        risk_code="IT-003",
        risk_name="脆弱性管理の不備",
        category="access_control",
        subcategory="vulnerability_management",
        description="OSS/サードパーティライブラリの脆弱性パッチ適用の遅延。",
        default_likelihood=4,
        default_impact=4,
        regulatory_ref="ISO 27001 A.12.6",
        applicable_assertions=["完全性"],
        tags=["security", "vulnerability", "patch"],
    ),
    # ── 開発管理 ──
    RiskItem(
        risk_code="IT-004",
        risk_name="ソースコード管理の不備",
        category="it_general",
        subcategory="source_control",
        description="リポジトリのアクセス制御・ブランチ保護・コードレビュープロセスの不備。",
        default_likelihood=3,
        default_impact=4,
        regulatory_ref="ISO 27001 A.14",
        applicable_assertions=["完全性", "存在性"],
        tags=["sdlc", "git", "code_review"],
    ),
    RiskItem(
        risk_code="IT-005",
        risk_name="CI/CDパイプラインのセキュリティ不備",
        category="it_general",
        subcategory="cicd_security",
        description="ビルド・デプロイパイプラインへの不正介入リスク。シークレット管理不備。",
        default_likelihood=3,
        default_impact=5,
        regulatory_ref="ISO 27001 A.14.2",
        applicable_assertions=["完全性"],
        tags=["sdlc", "cicd", "supply_chain"],
    ),
    # ── 収益認識 ──
    RiskItem(
        risk_code="IT-006",
        risk_name="SaaS収益認識の誤り",
        category="financial_process",
        subcategory="revenue_recognition",
        description="サブスクリプション収益の期間按分・繰延処理の誤り。",
        default_likelihood=3,
        default_impact=4,
        regulatory_ref="IFRS 15 / J-SOX",
        applicable_assertions=["期間帰属", "評価", "完全性"],
        tags=["revenue", "saas", "subscription"],
    ),
    RiskItem(
        risk_code="IT-007",
        risk_name="プロジェクト原価の過小計上",
        category="financial_process",
        subcategory="project_costing",
        description="受託開発プロジェクトの工数・原価集計の不備。進捗度見積り誤り。",
        default_likelihood=3,
        default_impact=3,
        regulatory_ref="IFRS 15 / J-SOX",
        applicable_assertions=["評価", "完全性"],
        tags=["project", "cost", "percentage_of_completion"],
    ),
    # ── サービス運用 ──
    RiskItem(
        risk_code="IT-008",
        risk_name="SLA未達による違約リスク",
        category="compliance",
        subcategory="sla_management",
        description="可用性・応答時間等のSLA未達によるペナルティ・信頼低下。",
        default_likelihood=3,
        default_impact=3,
        applicable_assertions=["権利と義務"],
        tags=["sla", "availability", "service"],
    ),
    RiskItem(
        risk_code="IT-009",
        risk_name="インシデント対応の遅延",
        category="it_general",
        subcategory="incident_management",
        description="セキュリティインシデントの検知・初動対応の遅延。報告義務の不履行。",
        default_likelihood=3,
        default_impact=5,
        regulatory_ref="ISO 27001 A.16",
        applicable_assertions=["完全性"],
        tags=["incident", "response", "security"],
    ),
    # ── コンプライアンス ──
    RiskItem(
        risk_code="IT-010",
        risk_name="ライセンス管理の不備",
        category="compliance",
        subcategory="license_management",
        description="OSS・商用ソフトウェアのライセンス遵守不備。コンプライアンスリスク。",
        default_likelihood=3,
        default_impact=3,
        regulatory_ref="著作権法",
        applicable_assertions=["完全性", "権利と義務"],
        tags=["license", "oss", "compliance"],
    ),
]

_IT_CONTROLS: list[ControlItem] = [
    # クラウドセキュリティ
    ControlItem(
        control_code="IC-001",
        control_name="クラウドセキュリティ構成レビュー",
        risk_code="IT-001",
        control_type="detective",
        frequency="weekly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="AWS/Azure Security Hub等を用いた構成ドリフト検知。",
        automation_level="full_auto",
    ),
    ControlItem(
        control_code="IC-002",
        control_name="IAMアクセスレビュー",
        risk_code="IT-001",
        control_type="detective",
        frequency="monthly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="IAMロール・ポリシーの棚卸と最小権限原則の検証。",
        automation_level="semi_auto",
    ),
    # データ保護
    ControlItem(
        control_code="IC-003",
        control_name="データ暗号化チェック",
        risk_code="IT-002",
        control_type="preventive",
        frequency="monthly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="保存データ・通信データの暗号化状態の確認。",
        automation_level="full_auto",
    ),
    # 脆弱性管理
    ControlItem(
        control_code="IC-004",
        control_name="脆弱性スキャン・パッチ管理",
        risk_code="IT-003",
        control_type="detective",
        frequency="weekly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="自動脆弱性スキャン（Dependabot等）と緊急パッチ適用状況。",
        automation_level="full_auto",
    ),
    # ソースコード管理
    ControlItem(
        control_code="IC-005",
        control_name="コードレビュー必須化",
        risk_code="IT-004",
        control_type="preventive",
        frequency="daily",
        test_approach="inspection",
        recommended_sample_size=25,
        description="PRマージ前の必須コードレビュー。ブランチ保護ルール。",
        automation_level="semi_auto",
    ),
    # CI/CD
    ControlItem(
        control_code="IC-006",
        control_name="CI/CDパイプラインセキュリティ",
        risk_code="IT-005",
        control_type="preventive",
        frequency="monthly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="シークレット管理・パイプライン設定の定期レビュー。",
    ),
    # SaaS収益
    ControlItem(
        control_code="IC-007",
        control_name="サブスクリプション収益照合",
        risk_code="IT-006",
        control_type="detective",
        frequency="monthly",
        test_approach="reperformance",
        recommended_sample_size=25,
        description="契約データと会計システムの収益計上額の照合。",
    ),
    # インシデント
    ControlItem(
        control_code="IC-008",
        control_name="インシデント対応訓練",
        risk_code="IT-009",
        control_type="preventive",
        frequency="quarterly",
        test_approach="inquiry",
        recommended_sample_size=0,
        description="セキュリティインシデント対応手順の訓練と改善。",
    ),
    # ライセンス
    ControlItem(
        control_code="IC-009",
        control_name="ソフトウェアライセンス棚卸",
        risk_code="IT-010",
        control_type="detective",
        frequency="quarterly",
        test_approach="inspection",
        recommended_sample_size=0,
        description="OSS・商用ライセンスのコンプライアンス棚卸。",
    ),
]


def get_it_services_template() -> IndustryTemplateDefinition:
    """IT業テンプレートを生成"""
    return IndustryTemplateDefinition(
        industry_code="it_services",
        industry_name="IT・SaaS",
        region="JP",
        version="1.0",
        description="IT・SaaS事業者向けリスク・統制テンプレート。クラウドセキュリティ・開発管理・サービス運用に特化。",
        regulatory_framework="ISO 27001 / J-SOX",
        risks=_IT_RISKS,
        controls=_IT_CONTROLS,
    )
