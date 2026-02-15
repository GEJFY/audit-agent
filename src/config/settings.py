"""アプリケーション設定 — pydantic-settings ベース"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全環境変数を型安全に管理"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────
    app_name: str = "audit-agent"
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    app_log_level: str = "DEBUG"
    secret_key: str = "change-me-in-production"  # noqa: S105

    # ── Database ──────────────────────────────────────
    database_url: str = "postgresql+asyncpg://audit_user:audit_pass@localhost:5432/audit_agent"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # ── JWT ───────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"  # noqa: S105
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Anthropic ─────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model_primary: str = "claude-sonnet-4-5-20250929"
    anthropic_model_fast: str = "claude-haiku-4-5-20251001"
    anthropic_max_tokens: int = 4096
    anthropic_timeout: int = 60

    # ── Azure OpenAI (Fallback) ──────────────────────
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-10-01-preview"
    azure_openai_deployment: str = ""

    # ── Azure AD (SharePoint, Email) ─────────────────
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    sharepoint_site_url: str = ""

    # ── SAP ──────────────────────────────────────────
    sap_base_url: str = ""
    sap_username: str = ""
    sap_password: str = ""
    sap_client_id: str = ""

    # ── Box ─────────────────────────────────────────
    box_client_id: str = ""
    box_client_secret: str = ""
    box_enterprise_id: str = ""

    # ── Notifications ─────────────────────────────────
    slack_webhook_url: str = ""
    teams_webhook_url: str = ""

    # ── Dialogue Bus ───────────────────────────────────
    dialogue_bus_backend: str = "memory"  # "memory", "redis", or "kafka"

    # ── Kafka ────────────────────────────────────────
    kafka_bootstrap_servers: str = ""
    kafka_topic_dialogue: str = "audit-agent-dialogue"

    # ── Temporal ─────────────────────────────────────
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "audit-agent"

    # ── Datadog ──────────────────────────────────────
    datadog_api_key: str = ""
    dd_service: str = "audit-agent"
    dd_env: str = "development"

    # ── LangSmith ─────────────────────────────────────
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "audit-agent"

    # ── Region / APAC ────────────────────────────────
    default_region: str = "JP"
    supported_regions: list[str] = ["JP", "SG", "HK", "AU", "TW", "KR", "TH"]

    # ── AWS ───────────────────────────────────────────
    aws_region: str = "ap-northeast-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket_evidence: str = "audit-agent-evidence"
    s3_bucket_reports: str = "audit-agent-reports"

    # ── Encryption ────────────────────────────────────
    encryption_key: str = ""

    # ── Monitoring ────────────────────────────────────
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    sentry_dsn: str = ""

    # ── CORS ──────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """JSON文字列またはリストを受け付ける"""
        if isinstance(v, str):
            import json

            return json.loads(v)  # type: ignore[no-any-return]
        return v  # type: ignore[no-any-return]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """設定シングルトンを返す"""
    return Settings()
