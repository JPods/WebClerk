/**
 * AiHelpWidget.tsx — Floating AI assistant chat widget.
 *
 * Renders a fixed-position button that expands into a chat panel.
 * Uses the RAG-powered /wcapi/ai/ask/ endpoint for context-aware answers.
 *
 * Place in App.tsx alongside other floating widgets:
 *   <AiHelpWidget position="bottom-right" />
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X, Send, ThumbsUp, ThumbsDown, Loader2, Bot } from "lucide-react";
import { askAi, submitFeedback } from "../apps/support/services/aiApi";
import type { AiSource } from "../apps/support/services/aiApi";

// ── Types ───────────────────────────────────────────────────────

interface AiHelpWidgetProps {
  position?: "bottom-right" | "bottom-left";
}

interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  sources?: AiSource[];
  feedback?: number | null;
  loading?: boolean;
}

// ── Position styles ─────────────────────────────────────────────

const positionStyles: Record<string, React.CSSProperties> = {
  "bottom-right": { position: "fixed", bottom: 24, right: 24, zIndex: 9998 },
  "bottom-left": { position: "fixed", bottom: 24, left: 24, zIndex: 9998 },
};

// ── Component ───────────────────────────────────────────────────

export const AiHelpWidget: React.FC<AiHelpWidgetProps> = ({
  position = "bottom-right",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    // Add loading placeholder
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", loading: true },
    ]);

    try {
      const contextPage = window.location.pathname;
      const result = await askAi({
        question,
        conversation_id: conversationId,
        context_page: contextPage,
      });

      setConversationId(result.conversation_id);
      setMessages((prev) => [
        ...prev.slice(0, -1), // Remove loading placeholder
        {
          id: result.message_id,
          role: "assistant",
          content: result.answer,
          sources: result.sources,
          feedback: null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content:
            "Sorry, I couldn't get an answer right now. Please check that the AI service is running.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, conversationId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFeedback = async (msgIndex: number, value: 1 | -1) => {
    const msg = messages[msgIndex];
    if (!msg.id) return;

    try {
      await submitFeedback(msg.id, value);
      setMessages((prev) =>
        prev.map((m, i) => (i === msgIndex ? { ...m, feedback: value } : m))
      );
    } catch {
      // Silently fail — feedback is non-critical
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setConversationId(null);
  };

  // ── Render ──────────────────────────────────────────────────

  // Collapsed state — just the button
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={positionStyles[position]}
        className="flex items-center justify-center w-14 h-14 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 transition-all hover:scale-105"
        title="AI Help Assistant"
      >
        <Bot className="w-6 h-6" />
      </button>
    );
  }

  // Expanded chat panel
  return (
    <div
      style={positionStyles[position]}
      className="flex flex-col w-96 h-[32rem] bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-blue-600 text-white">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5" />
          <span className="font-semibold text-sm">AI Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleNewChat}
            className="px-2 py-1 text-xs rounded hover:bg-blue-500 transition-colors"
            title="New conversation"
          >
            New
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded hover:bg-blue-500 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">
            <Bot className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-medium">CommerceExpert AI Assistant</p>
            <p className="mt-1">
              Ask about orders, invoices, inventory, API usage, or any feature.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {msg.loading ? (
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              ) : (
                <>
                  <div className="whitespace-pre-wrap">{msg.content}</div>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                      Sources: {msg.sources.map((s) => s.source).join(", ")}
                    </div>
                  )}

                  {/* Feedback buttons for assistant messages */}
                  {msg.role === "assistant" && !msg.loading && msg.id && (
                    <div className="flex items-center gap-1 mt-2 pt-1 border-t border-gray-200">
                      <button
                        onClick={() => handleFeedback(i, 1)}
                        className={`p-1 rounded transition-colors ${
                          msg.feedback === 1
                            ? "text-green-600"
                            : "text-gray-400 hover:text-green-500"
                        }`}
                        title="Helpful"
                      >
                        <ThumbsUp className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => handleFeedback(i, -1)}
                        className={`p-1 rounded transition-colors ${
                          msg.feedback === -1
                            ? "text-red-600"
                            : "text-gray-400 hover:text-red-500"
                        }`}
                        title="Not helpful"
                      >
                        <ThumbsDown className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-gray-200 bg-gray-50">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          disabled={isLoading}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default AiHelpWidget;
