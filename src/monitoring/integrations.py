"""外部監視サービス統合 — LangSmith / Datadog / Sentry"""

from typing import Any

from loguru import logger

from src.config.settings import get_settings


def setup_sentry() -> None:
    """Sentry SDK初期化 — エラートラッキング"""
    settings = get_settings()
    if not settings.sentry_dsn:
        logger.info("Sentry: DSN未設定、スキップ")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.loguru import LoguruIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release=f"audit-agent@{_get_version()}",
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            profiles_sample_rate=0.1 if settings.is_production else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoguruIntegration(),
            ],
            # PII送信防止
            send_default_pii=False,
            # パフォーマンスモニタリング
            enable_tracing=True,
            # 環境タグ
            tags={
                "service": settings.dd_service,
                "environment": settings.app_env,
            },
        )
        logger.info("Sentry初期化完了: env={}", settings.app_env)
    except ImportError:
        logger.warning("Sentry SDK未インストール")
    except Exception as e:
        logger.error("Sentry初期化エラー: {}", str(e))


def setup_datadog() -> None:
    """Datadog APM初期化 — 分散トレーシング"""
    settings = get_settings()
    if not settings.datadog_api_key:
        logger.info("Datadog: API Key未設定、スキップ")
        return

    try:
        from ddtrace import config, patch_all, tracer

        # 自動パッチ
        patch_all(
            fastapi=True,
            sqlalchemy=True,
            httpx=True,
            redis=True,
            logging=True,
        )

        # サービス設定
        config.fastapi["service_name"] = settings.dd_service
        config.fastapi["analytics_enabled"] = True

        # トレーサー設定
        tracer.configure(
            hostname="localhost",  # Datadog Agent
            port=8126,
        )

        # カスタムタグ
        tracer.set_tags(
            {
                "env": settings.dd_env,
                "service": settings.dd_service,
                "version": _get_version(),
            }
        )

        logger.info(
            "Datadog APM初期化完了: service={}, env={}",
            settings.dd_service,
            settings.dd_env,
        )
    except ImportError:
        logger.warning("ddtrace未インストール")
    except Exception as e:
        logger.error("Datadog初期化エラー: {}", str(e))


def setup_langsmith() -> None:
    """LangSmith初期化 — LLMトレーシング・評価"""
    settings = get_settings()
    if not settings.langchain_api_key:
        logger.info("LangSmith: API Key未設定、スキップ")
        return

    try:
        import os

        # LangSmith環境変数設定
        os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

        # 接続テスト
        from langsmith import Client

        _client = Client()
        # プロジェクト確認
        logger.info(
            "LangSmith初期化完了: project={}",
            settings.langchain_project,
        )
    except ImportError:
        logger.warning("langsmith未インストール")
    except Exception as e:
        logger.error("LangSmith初期化エラー: {}", str(e))


class DatadogMetrics:
    """Datadog カスタムメトリクス送信"""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._statsd: Any = None

    def _get_statsd(self) -> Any:
        """DogStatsDクライアント取得"""
        if self._statsd:
            return self._statsd
        try:
            from datadog import DogStatsd

            self._statsd = DogStatsd(
                host="localhost",
                port=8125,
                constant_tags=[
                    f"service:{self._settings.dd_service}",
                    f"env:{self._settings.dd_env}",
                ],
            )
        except ImportError:
            pass
        return self._statsd

    def increment(self, metric: str, value: int = 1, tags: list[str] | None = None) -> None:
        """カウンターインクリメント"""
        client = self._get_statsd()
        if client:
            client.increment(metric, value, tags=tags)

    def gauge(self, metric: str, value: float, tags: list[str] | None = None) -> None:
        """ゲージ値送信"""
        client = self._get_statsd()
        if client:
            client.gauge(metric, value, tags=tags)

    def histogram(self, metric: str, value: float, tags: list[str] | None = None) -> None:
        """ヒストグラム値送信"""
        client = self._get_statsd()
        if client:
            client.histogram(metric, value, tags=tags)

    def timing(self, metric: str, value_ms: float, tags: list[str] | None = None) -> None:
        """タイミング送信"""
        client = self._get_statsd()
        if client:
            client.timing(metric, value_ms, tags=tags)


class LangSmithTracer:
    """LangSmithカスタムトレーサー — Agent実行トレース"""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._enabled = bool(self._settings.langchain_api_key)

    def trace_agent_execution(
        self,
        agent_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Agent実行をLangSmithにトレース"""
        if not self._enabled:
            return

        try:
            from langsmith.run_trees import RunTree

            run = RunTree(
                name=f"agent:{agent_name}",
                run_type="chain",
                inputs=input_data,
                project_name=self._settings.langchain_project,
                extra=metadata or {},
            )
            run.end(outputs=output_data)
            run.post()
        except Exception as e:
            logger.debug("LangSmithトレースエラー: {}", str(e))

    def trace_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """LLM呼び出しをLangSmithにトレース"""
        if not self._enabled:
            return

        try:
            from langsmith.run_trees import RunTree

            run = RunTree(
                name=f"llm:{model}",
                run_type="llm",
                inputs={"prompt": prompt[:500]},
                project_name=self._settings.langchain_project,
                extra={
                    "model": model,
                    "tokens": tokens_used,
                    "cost_usd": cost_usd,
                },
            )
            run.end(outputs={"response": response[:500]})
            run.post()
        except Exception as e:
            logger.debug("LangSmithトレースエラー: {}", str(e))


def setup_all_integrations() -> None:
    """全外部監視サービスを初期化"""
    setup_sentry()
    setup_datadog()
    setup_langsmith()
    logger.info("外部監視統合初期化完了")


def _get_version() -> str:
    """バージョン取得"""
    try:
        from src import __version__

        return __version__
    except Exception:
        return "0.0.0"
