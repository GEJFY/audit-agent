"""Prometheus メトリクス定義"""

from prometheus_client import Counter, Gauge, Histogram, Info

# ── アプリケーション情報 ──────────────────────────────
app_info = Info("audit_agent", "アプリケーション情報")

# ── API メトリクス ────────────────────────────────────
http_requests_total = Counter(
    "http_requests_total",
    "HTTPリクエスト総数",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTPリクエスト処理時間",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── Agent メトリクス ──────────────────────────────────
agent_executions_total = Counter(
    "agent_executions_total",
    "Agent実行回数",
    ["agent_type", "status"],
)

agent_execution_duration_seconds = Histogram(
    "agent_execution_duration_seconds",
    "Agent実行時間",
    ["agent_type"],
    buckets=[0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

agent_confidence_score = Histogram(
    "agent_confidence_score",
    "Agent信頼度スコア分布",
    ["agent_type"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

# ── LLM メトリクス ────────────────────────────────────
llm_requests_total = Counter(
    "llm_requests_total",
    "LLM APIリクエスト数",
    ["provider", "model", "status"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLMトークン使用量",
    ["provider", "model", "direction"],  # direction: input/output
)

llm_cost_total = Counter(
    "llm_cost_total",
    "LLM APIコスト（USD）",
    ["provider", "model"],
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API応答時間",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# ── Dialogue メトリクス ───────────────────────────────
dialogue_messages_total = Counter(
    "dialogue_messages_total",
    "対話メッセージ数",
    ["message_type", "direction"],  # direction: auditor_to_auditee / auditee_to_auditor
)

escalations_total = Counter(
    "escalations_total",
    "エスカレーション発生数",
    ["reason", "severity"],
)

# ── Connector メトリクス ──────────────────────────────
connector_requests_total = Counter(
    "connector_requests_total",
    "コネクタリクエスト総数",
    ["connector", "method", "status"],  # status: success/failure
)

connector_request_duration_seconds = Histogram(
    "connector_request_duration_seconds",
    "コネクタリクエスト処理時間",
    ["connector", "method"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

connector_circuit_breaker_state = Gauge(
    "connector_circuit_breaker_state",
    "サーキットブレーカー状態 (0=closed, 1=open)",
    ["connector"],
)

connector_circuit_breaker_failures = Gauge(
    "connector_circuit_breaker_failures",
    "サーキットブレーカー連続失敗数",
    ["connector"],
)

# ── DB メトリクス ─────────────────────────────────────
db_pool_size = Gauge(
    "db_pool_size",
    "DBコネクションプールサイズ",
    ["pool_name"],
)

db_pool_checked_out = Gauge(
    "db_pool_checked_out",
    "使用中DBコネクション数",
    ["pool_name"],
)
