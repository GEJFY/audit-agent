/** バックエンド Pydantic スキーマ対応 TypeScript 型定義 */

// ── Auth ────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface TokenPayload {
  sub: string;
  tenant_id: string;
  role: string;
  exp: number;
}

// ── User ────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  is_active: boolean;
}

// ── Project ─────────────────────────────────────
export interface AuditProject {
  id: string;
  name: string;
  description: string;
  status: "draft" | "planning" | "fieldwork" | "reporting" | "completed";
  fiscal_year: number;
  department: string;
  created_at: string;
  updated_at: string;
}

// ── Agent ───────────────────────────────────────
export interface AgentInfo {
  name: string;
  description: string;
}

export interface AgentDecision {
  id: string;
  agent_type: string;
  decision_type: string;
  reasoning: string | null;
  confidence: number;
  model_used: string;
  human_approved: boolean | null;
  project_id: string | null;
  created_at: string | null;
}

export interface AgentExecuteRequest {
  agent_name: string;
  project_id?: string;
  parameters?: Record<string, unknown>;
}

export interface AgentExecuteResponse {
  agent_name: string;
  status: string;
  message: string;
  execution_id: string;
  result?: Record<string, unknown>;
}

// ── Dialogue ────────────────────────────────────
export interface DialogueMessage {
  id: string;
  from_agent: string;
  to_agent: string | null;
  message_type: "question" | "answer" | "clarification" | "escalation";
  content: string;
  thread_id: string;
  quality_score: number | null;
  timestamp: string;
}

// ── Approval ────────────────────────────────────
export interface ApprovalQueueItem {
  id: string;
  decision_id: string;
  approval_type: string;
  priority: string;
  status: string;
  requested_by_agent: string;
  context: Record<string, unknown>;
  created_at: string | null;
}

// ── Evidence ────────────────────────────────────
export interface EvidenceItem {
  id: string;
  name: string;
  type: "document" | "spreadsheet" | "screenshot" | "email" | "log" | "other";
  source: "upload" | "box" | "sharepoint" | "manual";
  file_size: number;
  mime_type: string;
  project_id: string | null;
  uploaded_by: string | null;
  description: string;
  tags: string[];
  status: "pending" | "verified" | "rejected";
  created_at: string;
  updated_at: string;
}

export interface EvidenceUploadRequest {
  file: File;
  description: string;
  project_id?: string;
  tags?: string[];
}

export interface BoxSearchResult {
  id: string;
  name: string;
  type: string;
  size: number;
  created_at: string;
  modified_at: string;
  parent_folder: string | null;
  source: "box";
}

// ── API Response ────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}
