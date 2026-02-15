"""Workflow定義テスト — Temporal Workflow構造の検証"""

import pytest


@pytest.mark.unit
class TestAuditProjectWorkflow:
    """監査ワークフロー定義のテスト"""

    def test_workflow_init(self) -> None:
        """ワークフロー初期化"""
        from src.workflows.audit_workflow import AuditProjectWorkflow

        wf = AuditProjectWorkflow()
        assert wf._current_phase == "init"
        assert wf._is_cancelled is False
        assert wf._approval_pending is False

    def test_error_result(self) -> None:
        """エラー結果生成"""
        from src.workflows.audit_workflow import AuditProjectWorkflow

        wf = AuditProjectWorkflow()
        wf._state = {"project_id": "p-001"}

        result = wf._error_result("テストエラー", "詳細情報")

        assert result["workflow_status"] == "error"
        assert result["workflow_error"] == "テストエラー"
        assert result["workflow_error_detail"] == "詳細情報"

    def test_error_result_without_detail(self) -> None:
        """詳細なしエラー結果"""
        from src.workflows.audit_workflow import AuditProjectWorkflow

        wf = AuditProjectWorkflow()
        wf._state = {}

        result = wf._error_result("エラー")

        assert result["workflow_status"] == "error"
        assert "workflow_error_detail" not in result


@pytest.mark.unit
class TestAuditeeResponseWorkflow:
    """被監査回答ワークフロー定義のテスト"""

    def test_workflow_init(self) -> None:
        """ワークフロー初期化"""
        from src.workflows.auditee_workflow import AuditeeResponseWorkflow

        wf = AuditeeResponseWorkflow()
        assert wf._approved is False


@pytest.mark.unit
class TestControlsMonitoringWorkflow:
    """統制モニタリングワークフロー定義のテスト"""

    def test_workflow_init(self) -> None:
        """ワークフロー初期化"""
        from src.workflows.auditee_workflow import ControlsMonitoringWorkflow

        wf = ControlsMonitoringWorkflow()
        assert wf._state == {}
