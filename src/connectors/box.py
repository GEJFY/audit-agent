"""Box コネクタ — Box API経由で証跡ファイル検索・取得

Box Platform API (OAuth 2.0 / JWT認証) を使用して、
Box上のフォルダ・ファイルを検索し、証跡として取得する。

設定:
  BOX_CLIENT_ID: Box アプリケーション Client ID
  BOX_CLIENT_SECRET: Box アプリケーション Client Secret
  BOX_ENTERPRISE_ID: Box Enterprise ID（JWT認証用）
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from src.config.settings import get_settings
from src.connectors.base import (
    RETRYABLE_EXCEPTIONS,
    BaseConnector,
    connector_retry,
    with_circuit_breaker,
)


class BoxConnector(BaseConnector):
    """Box コネクタ

    Box Content API を使用して:
    - フォルダ内ファイル一覧取得
    - コンテンツ検索（全文検索）
    - ファイルメタデータ取得
    - ファイルダウンロード URL 取得
    """

    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()
        self._client_id = settings.box_client_id
        self._client_secret = settings.box_client_secret
        self._enterprise_id = settings.box_enterprise_id
        self._access_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def connector_name(self) -> str:
        return "box"

    async def connect(self) -> bool:
        """Box OAuth 2.0 Client Credentials Grant でアクセストークン取得"""
        if not all([self._client_id, self._client_secret]):
            logger.warning("Box: API設定が不完全です")
            return False

        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            response = await self._client.post(
                "https://api.box.com/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "box_subject_type": "enterprise",
                    "box_subject_id": self._enterprise_id,
                },
            )
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            logger.info("Box: 接続成功")
            return True
        except Exception as e:
            logger.error(f"Box: 接続失敗 — {e}")
            return False

    async def disconnect(self) -> None:
        """接続切断"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None
        logger.info("Box: 切断")

    @connector_retry
    @with_circuit_breaker
    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Box全文検索

        Args:
            query: 検索クエリ
            **kwargs:
                folder_id: 検索対象フォルダID
                file_extensions: ファイル拡張子フィルタ (例: ["pdf", "xlsx"])
                content_types: コンテンツタイプ (例: ["name", "description", "file_content"])
                limit: 最大件数 (デフォルト: 20)
        """
        if not self._client or not self._access_token:
            logger.warning("Box: 未接続です")
            return []

        headers = {"Authorization": f"Bearer {self._access_token}"}

        params: dict[str, Any] = {
            "query": query,
            "limit": kwargs.get("limit", 20),
            "type": "file",
        }

        folder_id = kwargs.get("folder_id")
        if folder_id:
            params["ancestor_folder_ids"] = folder_id

        file_extensions = kwargs.get("file_extensions")
        if file_extensions:
            params["file_extensions"] = ",".join(file_extensions)

        content_types = kwargs.get("content_types")
        if content_types:
            params["content_types"] = ",".join(content_types)

        try:
            response = await self._client.get(
                "https://api.box.com/2.0/search",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for entry in data.get("entries", []):
                results.append(
                    {
                        "id": entry.get("id"),
                        "name": entry.get("name"),
                        "type": entry.get("type"),
                        "size": entry.get("size"),
                        "created_at": entry.get("created_at"),
                        "modified_at": entry.get("modified_at"),
                        "parent_folder": entry.get("parent", {}).get("name"),
                        "parent_folder_id": entry.get("parent", {}).get("id"),
                        "created_by": entry.get("created_by", {}).get("name"),
                        "shared_link": entry.get("shared_link", {}).get("url"),
                        "source": "box",
                    }
                )

            logger.info(f"Box: 検索完了 — {len(results)}件 (query={query})")
            return results

        except RETRYABLE_EXCEPTIONS:
            raise
        except Exception as e:
            logger.error(f"Box: 検索エラー — {e}")
            return []

    async def get_file_info(self, file_id: str) -> dict[str, Any] | None:
        """ファイルメタデータ取得"""
        if not self._client or not self._access_token:
            return None

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await self._client.get(
                f"https://api.box.com/2.0/files/{file_id}",
                headers=headers,
                params={"fields": "id,name,size,created_at,modified_at,parent,path_collection,shared_link"},
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except Exception as e:
            logger.error(f"Box: ファイル情報取得エラー — {e}")
            return None

    async def get_download_url(self, file_id: str) -> str | None:
        """ファイルダウンロードURL取得"""
        if not self._client or not self._access_token:
            return None

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await self._client.get(
                f"https://api.box.com/2.0/files/{file_id}/content",
                headers=headers,
                follow_redirects=False,
            )
            if response.status_code == 302:
                url: str | None = response.headers.get("location")
                return url
            return None
        except Exception as e:
            logger.error(f"Box: ダウンロードURL取得エラー — {e}")
            return None

    async def list_folder(self, folder_id: str = "0", limit: int = 100) -> list[dict[str, Any]]:
        """フォルダ内アイテム一覧"""
        if not self._client or not self._access_token:
            return []

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await self._client.get(
                f"https://api.box.com/2.0/folders/{folder_id}/items",
                headers=headers,
                params={"limit": limit, "fields": "id,name,type,size,modified_at"},
            )
            response.raise_for_status()
            data = response.json()
            entries: list[dict[str, Any]] = data.get("entries", [])
            return entries
        except Exception as e:
            logger.error(f"Box: フォルダ一覧エラー — {e}")
            return []

    async def health_check(self) -> bool:
        """接続チェック"""
        if not self._client or not self._access_token:
            return False
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = await self._client.get(
                "https://api.box.com/2.0/users/me",
                headers=headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Box health_check 失敗: {}", str(e))
            return False
