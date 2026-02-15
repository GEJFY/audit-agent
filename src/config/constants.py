"""アプリケーション定数定義"""

from enum import StrEnum


# ── テナントロール ────────────────────────────────────
class UserRole(StrEnum):
    ADMIN = "admin"
    AUDITOR = "auditor"
    AUDITEE_MANAGER = "auditee_manager"
    AUDITEE_USER = "auditee_user"
    VIEWER = "viewer"
    EXECUTIVE = "executive"  # CFO/CLO向けポートフォリオビュー


# ── 監査プロジェクトステータス ────────────────────────
class ProjectStatus(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    FIELDWORK = "fieldwork"
    REPORTING = "reporting"
    FOLLOW_UP = "follow_up"
    CLOSED = "closed"


# ── エージェント種別 ──────────────────────────────────
class AuditorAgentType(StrEnum):
    ORCHESTRATOR = "auditor_orchestrator"
    PLANNER = "auditor_planner"
    DATA_COLLECTOR = "auditor_data_collector"
    CONTROLS_TESTER = "auditor_controls_tester"
    ANOMALY_DETECTIVE = "auditor_anomaly_detective"
    REPORT_WRITER = "auditor_report_writer"
    FOLLOW_UP = "auditor_follow_up"
    KNOWLEDGE = "auditor_knowledge"


class AuditeeAgentType(StrEnum):
    ORCHESTRATOR = "auditee_orchestrator"
    RESPONSE = "auditee_response"
    EVIDENCE_SEARCH = "auditee_evidence_search"
    PREP = "auditee_prep"
    RISK_ALERT = "auditee_risk_alert"
    CONTROLS_MONITOR = "auditee_controls_monitor"


# ── 対話メッセージタイプ ──────────────────────────────
class DialogueMessageType(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    EVIDENCE_REQUEST = "evidence_request"
    EVIDENCE_SUBMIT = "evidence_submit"
    ESCALATION = "escalation"
    FOLLOW_UP = "follow_up"
    ACKNOWLEDGMENT = "acknowledgment"


# ── リスクレベル ──────────────────────────────────────
class RiskLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ── 検出結果ステータス ────────────────────────────────
class FindingStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REMEDIATION_PLANNED = "remediation_planned"
    REMEDIATED = "remediated"
    CLOSED = "closed"


# ── エスカレーション理由 ──────────────────────────────
class EscalationReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    HIGH_RISK_DETECTED = "high_risk_detected"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    POLICY_VIOLATION = "policy_violation"


# ── Agent動作モード ───────────────────────────────────
class AgentMode(StrEnum):
    AUDIT = "audit"  # 全判断に人間承認が必要
    ASSIST = "assist"  # 定型タスクは自動、重要判断は人間承認
    AUTONOMOUS = "autonomous"  # 自律実行（ログ記録のみ）


# ── 統制テスト結果 ────────────────────────────────────
class ControlTestResult(StrEnum):
    EFFECTIVE = "effective"
    INEFFECTIVE = "ineffective"
    NOT_TESTED = "not_tested"
    PARTIALLY_EFFECTIVE = "partially_effective"


# ── 定数値 ────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.75  # エスカレーション閾値
MAX_RETRY_ATTEMPTS = 3
EVIDENCE_MAX_SIZE_MB = 50
DIALOGUE_TIMEOUT_HOURS = 24
API_VERSION = "v1"

# ── Autonomous モード閾値 ──────────────────────────────
# エージェント別信頼度閾値（リスクティアに連動）
AGENT_CONFIDENCE_THRESHOLDS: dict[str, float] = {
    # LOW ティア (0.70)
    "auditor_data_collector": 0.70,
    "auditor_knowledge": 0.70,
    "auditee_evidence_search": 0.70,
    "auditee_prep": 0.70,
    "auditee_controls_monitor": 0.70,
    # MEDIUM ティア (0.85)
    "auditor_controls_tester": 0.85,
    "auditor_anomaly_detective": 0.85,
    "auditor_follow_up": 0.85,
    "auditee_orchestrator": 0.85,
    "auditee_response": 0.85,
    # HIGH ティア (0.92)
    "auditor_orchestrator": 0.92,
    "auditor_planner": 0.92,
    "auditor_report_writer": 0.92,
    "auditee_risk_alert": 0.92,
}

AUTONOMOUS_MAX_CONSECUTIVE_ERRORS = 5  # 自動停止閾値
AUTONOMOUS_AUTO_REVIEW_SAMPLE_RATE = 0.1  # 自動レビューサンプル率（10%）
