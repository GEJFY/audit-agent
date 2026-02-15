# audit-agent

Enterprise AI Audit Agent Platform - bidirectional auditor/auditee dialogue system with LangGraph state machines.

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
make test-unit

# Lint & format
make lint
make format
```

## Architecture

- **14 AI Agents** (8 auditor + 6 auditee) with LangGraph
- **Dialogue Bus** with Redis Streams + Kafka
- **LLM Gateway** multi-provider (Anthropic Claude, Azure OpenAI)
- **FastAPI** with JWT auth, RBAC, tenant isolation
- **PostgreSQL + pgvector** for semantic search
- **Temporal** workflow orchestration
