/**
 * aiApi.ts — API client for the AI Assistant endpoints.
 *
 * Endpoints:
 *   POST /wcapi/ai/ask/       — ask a question
 *   POST /wcapi/ai/feedback/  — submit feedback
 *   GET  /wcapi/ai/health/    — health check
 *   GET  /wcapi/ai/history/   — conversation history
 */
import apiClient from "../../api/axios";

// ── Types ───────────────────────────────────────────────────────

export interface AiSource {
  source: string;
  type: string;
  distance: number | null;
}

export interface AiAskRequest {
  question: string;
  conversation_id?: number | null;
  context_page?: string;
  stream?: boolean;
}

export interface AiAskResponse {
  answer: string;
  sources: AiSource[];
  model: string;
  conversation_id: number;
  message_id: number;
}

export interface AiHealthResponse {
  ollama_available: boolean;
  ollama_model: string;
  ollama_url: string;
  available_models: string[];
  vector_store: {
    collection: string;
    count: number;
    persist_dir: string;
  };
  status: "ok" | "degraded";
}

export interface AiMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  feedback: number | null;
  dt_created: string;
}

export interface AiConversation {
  id: number;
  context_page: string;
  dt_created: string;
  messages: AiMessage[];
}

// ── API functions ───────────────────────────────────────────────

export async function askAi(request: AiAskRequest): Promise<AiAskResponse> {
  const res = await apiClient.post("/wcapi/ai/ask/", request);
  return res.data.data;
}

export async function submitFeedback(
  messageId: number,
  feedback: 1 | -1
): Promise<void> {
  await apiClient.post("/wcapi/ai/feedback/", {
    message_id: messageId,
    feedback,
  });
}

export async function getAiHealth(): Promise<AiHealthResponse> {
  const res = await apiClient.get("/wcapi/ai/health/");
  return res.data.data;
}

export async function getAiHistory(): Promise<AiConversation[]> {
  const res = await apiClient.get("/wcapi/ai/history/");
  return res.data.data.conversations;
}
