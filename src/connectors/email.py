"""メールコネクタ — Microsoft Graph API / IMAP経由でメールアーカイブ検索"""

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


class EmailConnector(BaseConnector):
    """Exchange Online / Gmail メールコネクタ

    Microsoft Graph APIを使用してExchange Onlineのメールを検索。
    監査関連メールの検索・添付ファイル取得を行う。
    """

    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()
        self._tenant_id = settings.azure_tenant_id
        self._client_id = settings.azure_client_id
        self._client_secret = settings.azure_client_secret
        self._access_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def connector_name(self) -> str:
        return "email"

    async def connect(self) -> bool:
        """Microsoft Graph API認証"""
        if not all([self._tenant_id, self._client_id, self._client_secret]):
            logger.warning("Email: Azure AD設定が不完全です")
            return False

        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            response = await self._client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            response.raise_for_status()
            self._access_token = response.json()["access_token"]
            logger.info("Email接続成功 (Microsoft Graph)")
            return True
        except Exception as e:
            logger.error("Email接続エラー: {}", str(e))
            return False

    async def disconnect(self) -> None:
        """接続切断"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._access_token = None

    @connector_retry
    @with_circuit_breaker
    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        """メール検索 — Microsoft Graph Messages API

        Args:
            query: 検索クエリ文字列（件名、本文、送信者）
            kwargs:
                user_id: 検索対象ユーザーID（メールアドレス）
                folder: フォルダ名 (inbox, sentItems, archive)
                from_address: 送信者フィルタ
                date_from: 開始日 (YYYY-MM-DD)
                date_to: 終了日 (YYYY-MM-DD)
                has_attachments: 添付ファイルありのみ
                max_results: 最大件数 (default: 25)
        """
        if not self._access_token or not self._client:
            connected = await self.connect()
            if not connected:
                return []

        assert self._client is not None

        user_id = kwargs.get("user_id", "me")
        folder = kwargs.get("folder")
        from_address = kwargs.get("from_address")
        date_from = kwargs.get("date_from")
        date_to = kwargs.get("date_to")
        has_attachments = kwargs.get("has_attachments")
        max_results = kwargs.get("max_results", 25)

        # ODataフィルタ構築
        filter_parts: list[str] = []
        if query:
            # $search はトップレベルクエリ
            pass
        if from_address:
            filter_parts.append(f"from/emailAddress/address eq '{from_address}'")
        if date_from:
            filter_parts.append(f"receivedDateTime ge {date_from}T00:00:00Z")
        if date_to:
            filter_parts.append(f"receivedDateTime le {date_to}T23:59:59Z")
        if has_attachments:
            filter_parts.append("hasAttachments eq true")

        # URL構築
        if folder:
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/{folder}/messages"
        else:
            url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages"

        params: dict[str, str] = {
            "$top": str(max_results),
            "$select": "id,subject,bodyPreview,from,toRecipients,receivedDateTime,hasAttachments,importance,isRead",
            "$orderby": "receivedDateTime desc",
        }
        if query:
            params["$search"] = f'"{query}"'
        if filter_parts:
            params["$filter"] = " and ".join(filter_parts)

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = await self._client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            results: list[dict[str, Any]] = []
            for msg in data.get("value", []):
                results.append(
                    {
                        "id": msg.get("id", ""),
                        "subject": msg.get("subject", ""),
                        "body_preview": msg.get("bodyPreview", ""),
                        "from_name": (msg.get("from", {}).get("emailAddress", {}).get("name", "")),
                        "from_address": (msg.get("from", {}).get("emailAddress", {}).get("address", "")),
                        "to_recipients": [
                            r.get("emailAddress", {}).get("address", "") for r in msg.get("toRecipients", [])
                        ],
                        "received_datetime": msg.get("receivedDateTime", ""),
                        "has_attachments": msg.get("hasAttachments", False),
                        "importance": msg.get("importance", "normal"),
                        "source": "email",
                    }
                )

            logger.info("Email検索完了: query='{}', results={}", query, len(results))
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self._access_token = None
                await self.connect()
                return await self.search(query, **kwargs)
            logger.error("Email検索エラー: {}", str(e))
            return []
        except RETRYABLE_EXCEPTIONS:
            raise
        except Exception as e:
            logger.error("Email検索エラー: {}", str(e))
            return []

    async def get_attachments(self, user_id: str, message_id: str) -> list[dict[str, Any]]:
        """メール添付ファイル一覧取得"""
        if not self._access_token or not self._client:
            return []

        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            response = await self._client.get(
                f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{message_id}/attachments",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            return [
                {
                    "id": att.get("id", ""),
                    "name": att.get("name", ""),
                    "content_type": att.get("contentType", ""),
                    "size": att.get("size", 0),
                    "is_inline": att.get("isInline", False),
                }
                for att in data.get("value", [])
            ]
        except Exception as e:
            logger.error("Email添付取得エラー: {}", str(e))
            return []

    async def get_attachment_content(self, user_id: str, message_id: str, attachment_id: str) -> bytes | None:
        """添付ファイルコンテンツ取得"""
        if not self._access_token or not self._client:
            return None

        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            response = await self._client.get(
                f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{message_id}/attachments/{attachment_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            import base64

            content_bytes = data.get("contentBytes", "")
            if content_bytes:
                return base64.b64decode(content_bytes)
            return None
        except Exception as e:
            logger.error("Email添付コンテンツ取得エラー: {}", str(e))
            return None

    async def health_check(self) -> bool:
        """接続チェック"""
        if not self._access_token or not self._client:
            return False
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = await self._client.get(
                "https://graph.microsoft.com/v1.0/organization",
                headers=headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Email health_check 失敗: {}", str(e))
            return False
