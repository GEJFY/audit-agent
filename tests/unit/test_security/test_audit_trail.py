"""Audit Trail テスト"""

import pytest
from uuid import uuid4

from src.security.audit_trail import AuditTrailService, AuditEntry


@pytest.mark.unit
class TestAuditTrailService:
    """監査証跡サービスのユニットテスト"""

    def test_record(self, audit_trail: AuditTrailService) -> None:
        """基本記録テスト"""
        tenant_id = uuid4()
        entry = audit_trail.record(
            tenant_id=tenant_id,
            action="create",
            resource_type="project",
            resource_id="proj-001",
        )

        assert entry.tenant_id == tenant_id
        assert entry.action == "create"
        assert entry.resource_type == "project"
        assert entry.hash != ""

    def test_record_with_user(self, audit_trail: AuditTrailService) -> None:
        """ユーザー操作の記録"""
        tenant_id = uuid4()
        user_id = uuid4()

        entry = audit_trail.record(
            tenant_id=tenant_id,
            user_id=user_id,
            action="update",
            resource_type="finding",
            resource_id="find-001",
            details={"field": "status", "old": "open", "new": "resolved"},
        )

        assert entry.user_id == user_id
        assert entry.details["field"] == "status"

    def test_record_agent_decision(self, audit_trail: AuditTrailService) -> None:
        """Agent判断の記録"""
        tenant_id = uuid4()

        entry = audit_trail.record_agent_decision(
            tenant_id=tenant_id,
            agent_name="auditor_anomaly_detective",
            decision="anomaly_detected",
            reasoning="金額が3σを超過",
            confidence=0.85,
            resource_type="journal_entry",
            resource_id="JE-003",
            input_data={"amount": 50000000},
        )

        assert entry.agent_name == "auditor_anomaly_detective"
        assert entry.action == "agent_decision"
        assert entry.confidence == 0.85
        assert entry.details["decision"] == "anomaly_detected"
        assert entry.details["reasoning"] == "金額が3σを超過"

    def test_flush(self, audit_trail: AuditTrailService) -> None:
        """バッファフラッシュテスト"""
        tenant_id = uuid4()

        audit_trail.record(
            tenant_id=tenant_id,
            action="create",
            resource_type="project",
            resource_id="proj-001",
        )
        audit_trail.record(
            tenant_id=tenant_id,
            action="update",
            resource_type="project",
            resource_id="proj-001",
        )

        entries = audit_trail.flush()
        assert len(entries) == 2

        # フラッシュ後はバッファが空
        entries2 = audit_trail.flush()
        assert len(entries2) == 0

    def test_hash_chain_integrity(self, audit_trail: AuditTrailService) -> None:
        """ハッシュチェーンの整合性"""
        tenant_id = uuid4()

        entry1 = audit_trail.record(
            tenant_id=tenant_id,
            action="create",
            resource_type="project",
            resource_id="proj-001",
        )
        entry2 = audit_trail.record(
            tenant_id=tenant_id,
            action="update",
            resource_type="project",
            resource_id="proj-001",
        )

        # 異なるハッシュ値
        assert entry1.hash != entry2.hash
        # ハッシュは空でない
        assert len(entry1.hash) == 64
        assert len(entry2.hash) == 64

    def test_record_without_optional_fields(self, audit_trail: AuditTrailService) -> None:
        """オプショナルフィールドなしの記録"""
        tenant_id = uuid4()

        entry = audit_trail.record(
            tenant_id=tenant_id,
            action="read",
            resource_type="evidence",
            resource_id="ev-001",
        )

        assert entry.user_id is None
        assert entry.agent_name is None
        assert entry.confidence is None
        assert entry.details == {}
