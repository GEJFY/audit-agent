/** 対話 API 関数 */

import type { DialogueMessage, DialogueThread } from "@/types/api";
import { apiClient } from "./client";

export interface SendMessageInput {
  from_agent: string;
  to_agent?: string;
  message_type: "question" | "answer" | "clarification" | "escalation";
  content: string;
  thread_id?: string;
}

export async function sendMessage(
  input: SendMessageInput,
): Promise<DialogueMessage> {
  return apiClient.post<DialogueMessage>("/api/v1/dialogue/send", input);
}

export async function getThreadMessages(
  threadId: string,
): Promise<DialogueMessage[]> {
  return apiClient.get<DialogueMessage[]>(
    `/api/v1/dialogue/thread/${threadId}`,
  );
}

export async function getRecentMessages(
  limit: number = 20,
): Promise<DialogueMessage[]> {
  return apiClient.get<DialogueMessage[]>(
    `/api/v1/dialogue/messages?limit=${limit}`,
  );
}

export async function getThreads(): Promise<DialogueThread[]> {
  try {
    return await apiClient.get<DialogueThread[]>("/api/v1/dialogue/threads");
  } catch {
    return generateDemoThreads();
  }
}

function generateDemoThreads(): DialogueThread[] {
  return [
    {
      thread_id: "thread-001",
      subject: "FY2025 Journal Entry Review",
      participants: ["auditor_orchestrator", "controls_tester", "human"],
      message_count: 12,
      last_message_at: "2026-02-15T10:30:00Z",
      status: "active",
    },
    {
      thread_id: "thread-002",
      subject: "Access Control Findings Discussion",
      participants: ["anomaly_detective", "planner", "human"],
      message_count: 8,
      last_message_at: "2026-02-14T16:45:00Z",
      status: "active",
    },
    {
      thread_id: "thread-003",
      subject: "Q3 Self-Assessment Preparation",
      participants: ["auditee_orchestrator", "response_drafter"],
      message_count: 5,
      last_message_at: "2026-02-13T09:20:00Z",
      status: "resolved",
    },
    {
      thread_id: "thread-004",
      subject: "IT Change Management Escalation",
      participants: ["controls_tester", "auditor_orchestrator", "human"],
      message_count: 15,
      last_message_at: "2026-02-12T14:00:00Z",
      status: "escalated",
    },
    {
      thread_id: "thread-005",
      subject: "Vendor Due Diligence Evidence Request",
      participants: ["evidence_searcher", "auditee_orchestrator"],
      message_count: 3,
      last_message_at: "2026-02-11T11:15:00Z",
      status: "resolved",
    },
  ];
}
