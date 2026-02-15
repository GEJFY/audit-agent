# API Reference

Base URL: `/api/v1`

## Authentication

### POST /auth/login
ユーザーログイン。JWTアクセストークン+リフレッシュトークンを返却。

**Request:**
```json
{"email": "user@example.com", "password": "secret"}
```

**Response:**
```json
{"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}
```

### POST /auth/register
ユーザー登録。

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secret",
  "full_name": "Test User",
  "tenant_id": "uuid"
}
```

### POST /auth/refresh
トークンリフレッシュ。

### GET /auth/me
現在のユーザー情報を取得。

---

## Projects

### GET /projects/
プロジェクト一覧取得（ページネーション対応）。

**Query:** `?skip=0&limit=20`

**Response:**
```json
{"total": 10, "items": [...]}
```

### POST /projects/
プロジェクト作成。

**Request:**
```json
{
  "name": "FY2026 内部監査",
  "fiscal_year": 2026,
  "audit_type": "internal"
}
```

### GET /projects/{project_id}
プロジェクト詳細取得。

---

## Agents

### GET /agents/
利用可能なエージェント一覧。

### POST /agents/execute
エージェントを実行。

**Request:**
```json
{
  "agent_name": "auditor_planner",
  "state": {"project_id": "uuid", "tenant_id": "uuid"}
}
```

### GET /agents/decisions
意思決定レコード一覧（承認キュー）。

### POST /agents/decisions/{id}/approve
意思決定を承認。

---

## Dialogue

### GET /dialogue/messages
メッセージ一覧（ページネーション対応）。

### POST /dialogue/send
メッセージ送信。

**Request:**
```json
{
  "content": "テスト質問",
  "to_tenant_id": "uuid",
  "message_type": "question"
}
```

### GET /dialogue/threads/{thread_id}
スレッド内メッセージ取得。

---

## Evidence

### GET /evidence/
証跡一覧。

### POST /evidence/upload
証跡アップロード（multipart/form-data）。

### GET /evidence/{id}
証跡詳細取得。

### DELETE /evidence/{id}
証跡削除。

---

## Analytics

### POST /analytics/benchmark
業種ベンチマーク分析。

### POST /analytics/portfolio
ポートフォリオリスク集約。

---

## Reports

### POST /reports/executive-summary
エグゼクティブサマリー生成。

### POST /reports/markdown
マークダウン形式レポート生成。

### POST /reports/risk-forecast
リスク予測レポート生成。

---

## Compliance

### GET /compliance/status
リージョン別コンプライアンス状況取得。

**Query:** `?region=JP`

### POST /compliance/check
コンプライアンスチェック実行。

**Request:**
```json
{"region": "JP", "tenant_id": "uuid"}
```

---

## Health

### GET /health
ヘルスチェック。

### GET /health/ready
Readinessプローブ。

### GET /health/live
Livenessプローブ。

---

## WebSocket

### WS /ws/{user_id}
リアルタイム通知用WebSocket接続。

---

## Error Codes

| Code | Description |
|------|-------------|
| 401 | 認証エラー |
| 403 | 権限不足 / セキュリティブロック |
| 404 | リソース未発見 |
| 422 | バリデーションエラー |
| 429 | レート制限超過 |
| 500 | サーバーエラー |
