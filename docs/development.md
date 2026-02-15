# Development Guide

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Testing

### Unit Tests

```bash
# 全ユニットテスト
python -m pytest tests/unit/ -v

# カバレッジ付き
python -m pytest tests/unit/ --cov=src --cov-report=term-missing

# 特定モジュール
python -m pytest tests/unit/test_agents/ -v
python -m pytest tests/unit/test_api/ -v
python -m pytest tests/unit/test_db/ -v
```

### Test Structure

```
tests/
├── conftest.py              # 共通fixtures (mock_llm_gateway, etc.)
├── unit/
│   ├── test_agents/         # 14エージェントテスト
│   ├── test_api/            # APIルート・ミドルウェアテスト
│   ├── test_config/         # 設定・定数テスト
│   ├── test_connectors/     # コネクタテスト
│   ├── test_db/             # DBモデル・リポジトリテスト
│   ├── test_llm_gateway/    # LLMプロバイダーテスト
│   ├── test_monitoring/     # 監視・ヘルスチェックテスト
│   ├── test_notifications/  # 通知テスト
│   ├── test_reports/        # レポートテンプレートテスト
│   ├── test_risk_templates/ # リスク評価テスト
│   ├── test_security/       # セキュリティテスト
│   ├── test_storage/        # ストレージテスト
│   └── test_workflows/      # ワークフローテスト
└── integration/
    └── test_api.py          # API統合テスト
```

### Test Patterns

**Agent Tests** - LLMをモックし、状態遷移を検証:
```python
@pytest.fixture
def agent(mock_llm_gateway):
    a = SomeAgent(llm_gateway=mock_llm_gateway)
    a._audit_trail = MagicMock()
    return a

async def test_execute(agent, mock_llm_gateway):
    mock_llm_gateway.generate = AsyncMock(
        return_value=LLMResponse(content='{"key": "value"}', ...)
    )
    state = AuditorState(tenant_id="t-001", ...)
    result = await agent.execute(state)
    assert result.some_field == expected
```

**API Tests** - httpx AsyncClient + dependency overrides:
```python
@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

## Code Quality

```bash
# Lint
python -m ruff check src/ tests/

# Auto-fix
python -m ruff check src/ tests/ --fix

# Format
python -m ruff format src/ tests/

# Type check
python -m mypy src/
```

## Adding a New Agent

1. `src/agents/` に新しいエージェントファイルを作成
2. `BaseAuditAgent[StateType]` を継承
3. `agent_name`, `agent_description`, `execute()` を実装
4. `tests/unit/test_agents/` にテストを作成
5. 必要に応じて `src/agents/registry.py` に登録

```python
class NewAgent(BaseAuditAgent[AuditorState]):
    @property
    def agent_name(self) -> str:
        return "new_agent"

    @property
    def agent_description(self) -> str:
        return "新しいエージェント"

    async def execute(self, state: AuditorState) -> AuditorState:
        # LLM呼び出し
        response = await self._llm.generate(prompt)
        # 状態更新
        state.messages.append(AgentMessage(...))
        return state
```

## Adding a New API Endpoint

1. `src/api/routes/` にルーターファイルを作成
2. `src/api/main.py` の `create_app()` でルーターを登録
3. 必要に応じてPydanticスキーマを `src/api/schemas/` に追加
4. テストを `tests/unit/test_api/` に作成

## Frontend

```bash
cd frontend
npm install
npm run dev       # 開発サーバー
npm run build     # ビルド
npm run lint      # Lint
npm run typecheck # 型チェック
```
