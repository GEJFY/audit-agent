/** 対話 API 関数 */

import type { DialogueMessage } from "@/types/api";
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
