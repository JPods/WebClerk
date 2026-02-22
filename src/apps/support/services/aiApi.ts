/**
 * aiApi.ts — API client for the AI Assistant endpoints.
 *
 * Endpoints:
 *   POST /wcapi/ai/ask/       — ask a question (mode-aware)
 *   POST /wcapi/ai/debug/     — analyze an error/traceback
 *   POST /wcapi/ai/review/    — review code for conventions
 *   POST /wcapi/ai/generate/  — generate code or tests
 *   POST /wcapi/ai/feedback/  — submit feedback
 *   GET  /wcapi/ai/health/    — health check
 *   GET  /wcapi/ai/history/   — conversation history
 *   GET  /wcapi/ai/modes/     — list available modes
 *   POST /wcapi/ai/reindex/   — trigger reindex (staff)
 */
import apiClient from "../../../api/axios";

// ── Types ───────────────────────────────────────────────────────

export type AiMode =
  | "general"
  | "developer"
  | "debugger"
  | "user_support"
  | "code_review"
  | "test_writer";

export interface AiModeInfo {
  key: AiMode;
  label: string;
  description: string;
}

export interface AiSource {
  source: string;
  type: string;
  distance: number | null;
}

export interface AiAskRequest {
  question: string;
  conversation_id?: number | null;
  context_page?: string;
  mode?: AiMode;
  extra_context?: string;
  stream?: boolean;
}

export interface AiAskResponse {
  answer: string;
  sources: AiSource[];
  model: string;
  mode: AiMode;
  conversation_id: number;
  message_id: number;
}

export interface AiDebugRequest {
  error: string;
  file_context?: string;
  question?: string;
}

export interface AiDebugResponse {
  diagnosis: string;
  sources: AiSource[];
  model: string;
  mode: "debugger";
}

export interface AiReviewRequest {
  code: string;
  file_path?: string;
  question?: string;
}

export interface AiReviewResponse {
  review: string;
  sources: AiSource[];
  model: string;
  mode: "code_review";
}

export interface AiGenerateRequest {
  task: "test" | "code" | "migration";
  description: string;
  file_context?: string;
  target_file?: string;
}

export interface AiGenerateResponse {
  generated: string;
  sources: AiSource[];
  model: string;
  mode: AiMode;
  task: string;
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

// ── Core API ────────────────────────────────────────────────────

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

// ── Specialized endpoints ───────────────────────────────────────

export async function debugError(
  request: AiDebugRequest
): Promise<AiDebugResponse> {
  const res = await apiClient.post("/wcapi/ai/debug/", request);
  return res.data.data;
}

export async function reviewCode(
  request: AiReviewRequest
): Promise<AiReviewResponse> {
  const res = await apiClient.post("/wcapi/ai/review/", request);
  return res.data.data;
}

export async function generateCode(
  request: AiGenerateRequest
): Promise<AiGenerateResponse> {
  const res = await apiClient.post("/wcapi/ai/generate/", request);
  return res.data.data;
}

export async function getAiModes(): Promise<AiModeInfo[]> {
  const res = await apiClient.get("/wcapi/ai/modes/");
  return res.data.data.modes;
}

export async function triggerReindex(
  source: string = "all"
): Promise<{ message: string; total_chunks: number }> {
  const res = await apiClient.post("/wcapi/ai/reindex/", { source });
  return res.data.data;
}
