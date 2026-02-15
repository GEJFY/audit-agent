"""セルフアセスメント自動化ワークフローのテスト"""

import pytest

# temporalioが未インストールの場合はスキップ
pytest.importorskip("temporalio")


@pytest.mark.unit
class TestAssessmentConfig:
    """アセスメント設定のテスト"""

    def test_default_config(self) -> None:
        from src.workflows.self_assessment import AssessmentConfig

        config = AssessmentConfig()
        assert config.assessment_type == "quarterly"
        assert config.fiscal_year == 2026
        assert config.quarter == 1
        assert len(config.departments) == 4
        assert "finance" in config.departments
        assert config.auto_score is True
        assert config.require_approval is True
        assert config.approval_timeout_days == 7

    def test_custom_config(self) -> None:
        from src.workflows.self_assessment import AssessmentConfig

        config = AssessmentConfig(
            assessment_type="annual",
            fiscal_year=2025,
            quarter=4,
            departments=["finance", "it"],
            auto_score=False,
            require_approval=False,
            approval_timeout_days=14,
        )
        assert config.assessment_type == "annual"
        assert config.fiscal_year == 2025
        assert config.quarter == 4
        assert len(config.departments) == 2
        assert config.auto_score is False
        assert config.require_approval is False

    def test_default_control_categories(self) -> None:
        from src.workflows.self_assessment import AssessmentConfig

        config = AssessmentConfig()
        assert "access_control" in config.control_categories
        assert "financial_process" in config.control_categories
        assert "it_general" in config.control_categories
        assert "compliance" in config.control_categories


@pytest.mark.unit
class TestSelfAssessmentWorkflow:
    """ワークフロー定義のテスト"""

    def test_workflow_init(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        assert wf._state == {}
        assert wf._approved is False
        assert wf._rejection_reason == ""

    def test_parse_config_none(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        config = SelfAssessmentWorkflow._parse_config(None)
        assert config.assessment_type == "quarterly"
        assert config.fiscal_year == 2026

    def test_parse_config_partial(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        config = SelfAssessmentWorkflow._parse_config({"fiscal_year": 2025, "quarter": 3})
        assert config.fiscal_year == 2025
        assert config.quarter == 3
        assert config.assessment_type == "quarterly"

    def test_parse_config_full(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        config = SelfAssessmentWorkflow._parse_config(
            {
                "assessment_type": "ad_hoc",
                "fiscal_year": 2026,
                "quarter": 2,
                "departments": ["finance"],
                "control_categories": ["access_control"],
                "auto_score": False,
                "require_approval": False,
                "approval_timeout_days": 3,
            }
        )
        assert config.assessment_type == "ad_hoc"
        assert config.departments == ["finance"]
        assert config.control_categories == ["access_control"]
        assert config.auto_score is False
        assert config.approval_timeout_days == 3

    def test_get_state_initial(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        assert wf.get_state() == {}

    def test_get_progress_initial(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        progress = wf.get_progress()
        assert progress["current_phase"] == "unknown"
        assert progress["departments_completed"] == 0
        assert progress["departments_total"] == 0
        assert progress["overall_score"] == 0.0

    def test_get_progress_with_state(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        wf._state = {
            "current_phase": "collection",
            "departments": ["finance", "purchasing", "it"],
            "department_results": {
                "finance": {"status": "completed", "score": 85.0},
                "purchasing": {"status": "error", "error": "timeout"},
            },
            "overall_score": 42.5,
            "workflow_status": "in_progress",
        }
        progress = wf.get_progress()
        assert progress["current_phase"] == "collection"
        assert progress["departments_completed"] == 1
        assert progress["departments_total"] == 3
        assert progress["overall_score"] == 42.5

    async def test_approve_signal(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        assert wf._approved is False
        await wf.approve()
        assert wf._approved is True

    async def test_reject_signal(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        assert wf._rejection_reason == ""
        await wf.reject("スコアが低すぎるため再実施必要")
        assert wf._rejection_reason == "スコアが低すぎるため再実施必要"

    async def test_reject_signal_empty_reason(self) -> None:
        from src.workflows.self_assessment import SelfAssessmentWorkflow

        wf = SelfAssessmentWorkflow()
        await wf.reject("")
        assert wf._rejection_reason == "却下理由未記入"
