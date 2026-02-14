-- audit-agent データベース初期化SQL
-- pgvector拡張の有効化
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- アプリケーションユーザー（RLS用）
-- CREATE ROLE audit_app_user WITH LOGIN PASSWORD 'app_user_pass';
-- GRANT CONNECT ON DATABASE audit_agent TO audit_app_user;
