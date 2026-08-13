/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * AiHelpWidget.tsx — Floating AI assistant chat widget with mode switching
 * and browser console error capture.
 *
 * Modes:
 *   general      — Default conversational help
 *   developer    — Code-aware with file paths & conventions
 *   debugger     — Error analysis & fix suggestions (+ console capture)
 *   user_support — Plain-language help for end users
 *   code_review  — Convention compliance review
 *   test_writer  — Generate tests with project patterns
 *
 * Console Capture:
 *   Automatically hooks into console.error, window.onerror, and
 *   unhandled promise rejections. When in debugger mode, captured
 *   errors appear as clickable cards that can be sent to DeepSeek
 *   with one click, or you can paste errors manually via the paste panel.
 *
 * Place in App.tsx alongside other floating widgets:
 *   <AiHelpWidget position="bottom-right" />
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  X,
  Send,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  Bot,
  Bug,
  Code,
  HelpCircle,
  FileSearch,
  TestTube,
  ChevronDown,
  ClipboardPaste,
  AlertTriangle,
  Trash2,
} from "lucide-react";
import { askAi, debugError, submitFeedback } from "../apps/support/services/aiApi";
import type { AiSource, AiMode } from "../apps/support/services/aiApi";
import { useConsoleCapture } from "../hooks/useConsoleCapture";
import type { CapturedError } from "../hooks/useConsoleCapture";
import { formatDt } from '@/utils/fieldFormatters';

// ── Types ───────────────────────────────────────────────────────

interface AiHelpWidgetProps {
  position?: "bottom-right" | "bottom-left";
  defaultMode?: AiMode;
}

interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  sources?: AiSource[];
  feedback?: number | null;
  loading?: boolean;
  mode?: AiMode;
}

// ── Mode config ─────────────────────────────────────────────────

interface ModeConfig {
  key: AiMode;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
  placeholder: string;
  color: string;
}

const MODES: ModeConfig[] = [
  {
    key: "general",
    label: "General Help",
    shortLabel: "General",
    icon: <HelpCircle className="w-3.5 h-3.5" />,
    placeholder: "Ask about orders, invoices, inventory...",
    color: "bg-blue-600",
  },
  {
    key: "developer",
    label: "Developer",
    shortLabel: "Dev",
    icon: <Code className="w-3.5 h-3.5" />,
    placeholder: "How do I add a new model to WCAPI?",
    color: "bg-purple-600",
  },
  {
    key: "debugger",
    label: "Debugger",
    shortLabel: "Debug",
    icon: <Bug className="w-3.5 h-3.5" />,
    placeholder: "Paste an error or describe a bug...",
    color: "bg-red-600",
  },
  {
    key: "user_support",
    label: "User Support",
    shortLabel: "Support",
    icon: <HelpCircle className="w-3.5 h-3.5" />,
    placeholder: "How do I create a new customer?",
    color: "bg-green-600",
  },
  {
    key: "code_review",
    label: "Code Review",
    shortLabel: "Review",
    icon: <FileSearch className="w-3.5 h-3.5" />,
    placeholder: "Paste code to review for conventions...",
    color: "bg-amber-600",
  },
  {
    key: "test_writer",
    label: "Test Writer",
    shortLabel: "Tests",
    icon: <TestTube className="w-3.5 h-3.5" />,
    placeholder: "Write tests for OrderService.create...",
    color: "bg-teal-600",
  },
];

// ── Position styles ─────────────────────────────────────────────

const positionStyles: Record<string, React.CSSProperties> = {
  "bottom-right": { position: "fixed", bottom: 24, right: 24, zIndex: 9998 },
  "bottom-left": { position: "fixed", bottom: 24, left: 24, zIndex: 9998 },
};

// ── Component ───────────────────────────────────────────────────

export const AiHelpWidget: React.FC<AiHelpWidgetProps> = ({
  position = "bottom-right",
  defaultMode = "general",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [mode, setMode] = useState<AiMode>(defaultMode);
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [showPastePanel, setShowPastePanel] = useState(false);
  const [pasteContent, setPasteContent] = useState("");
  const [showCaptured, setShowCaptured] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);
  const pasteRef = useRef<HTMLTextAreaElement>(null);

  // Console error capture
  const { errors: capturedErrors, clearErrors, clearError } = useConsoleCapture();

  const currentMode = MODES.find((m) => m.key === mode) ?? MODES[0];

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

  // Close mode menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        modeMenuRef.current &&
        !modeMenuRef.current.contains(e.target as Node)
      ) {
        setShowModeMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: question, mode },
    ]);
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
        mode,
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
          mode: result.mode,
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
  }, [input, isLoading, conversationId, mode]);

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

  /**
   * Send an error (pasted or captured) to the AI debug endpoint.
   */
  const handleDebugError = useCallback(
    async (errorText: string, fileContext?: string) => {
      if (!errorText.trim() || isLoading) return;

      // Switch to debugger mode automatically
      setMode("debugger");
      setShowPastePanel(false);
      setShowCaptured(false);
      setPasteContent("");

      setMessages((prev) => [
        ...prev,
        { role: "user", content: errorText, mode: "debugger" },
      ]);
      setIsLoading(true);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", loading: true },
      ]);

      try {
        const result = await debugError({
          error: errorText,
          file_context: fileContext ?? window.location.pathname,
        });

        setMessages((prev) => [
          ...prev.slice(0, -1),
          {
            role: "assistant",
            content: result.diagnosis,
            sources: result.sources,
            feedback: null,
            mode: "debugger",
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev.slice(0, -1),
          {
            role: "assistant",
            content:
              "Sorry, I couldn't analyze that error. Please check that the AI service is running.",
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading]
  );

  /** Submit pasted console content */
  const handlePasteSubmit = () => {
    handleDebugError(pasteContent);
  };

  /** Send a captured error to the debugger */
  const handleSendCaptured = (captured: CapturedError) => {
    handleDebugError(captured.raw, captured.source);
    clearError(captured.id);
  };

  // Focus paste textarea when paste panel opens
  useEffect(() => {
    if (showPastePanel) {
      setTimeout(() => pasteRef.current?.focus(), 100);
    }
  }, [showPastePanel]);

  const selectMode = (m: AiMode) => {
    setMode(m);
    setShowModeMenu(false);
    inputRef.current?.focus();
  };

  // ── Render ──────────────────────────────────────────────────

  // Collapsed state — just the button
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        style={positionStyles[position]}
        className={`flex items-center justify-center w-14 h-14 rounded-full ${currentMode.color} text-white shadow-lg hover:opacity-90 transition-all hover:scale-105`}
        title="AI Help Assistant"
      >
        <Bot className="w-6 h-6" />
        {/* Error count badge when errors are captured */}
        {capturedErrors.length > 0 && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 text-[10px] font-bold text-white bg-red-500 rounded-full ring-2 ring-white">
            {capturedErrors.length > 9 ? "9+" : capturedErrors.length}
          </span>
        )}
      </button>
    );
  }

  // Expanded chat panel
  return (
    <div
      style={positionStyles[position]}
      className="flex flex-col w-96 h-[36rem] bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-3 ${currentMode.color} text-white`}
      >
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5" />
          <span className="font-semibold text-sm">AI Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          {/* Captured errors badge — only in debugger mode */}
          {mode === "debugger" && capturedErrors.length > 0 && (
            <button
              onClick={() => { setShowCaptured(!showCaptured); setShowPastePanel(false); }}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-red-500/30 hover:bg-red-500/50 transition-colors"
              title={`${capturedErrors.length} captured error${capturedErrors.length > 1 ? "s" : ""}`}
            >
              <AlertTriangle className="w-3 h-3" />
              <span>{capturedErrors.length}</span>
            </button>
          )}
          <button
            onClick={handleNewChat}
            className="px-2 py-1 text-xs rounded hover:bg-white/20 transition-colors"
            title="New conversation"
          >
            New
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded hover:bg-white/20 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Mode selector bar */}
      <div className="relative px-3 py-2 border-b border-gray-200 bg-gray-50">
        <div ref={modeMenuRef}>
          <button
            onClick={() => setShowModeMenu(!showModeMenu)}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            {currentMode.icon}
            <span>{currentMode.label}</span>
            <ChevronDown className="w-3 h-3 ml-1 text-gray-400" />
          </button>

          {showModeMenu && (
            <div className="absolute left-3 top-full mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1">
              {MODES.map((m) => (
                <button
                  key={m.key}
                  onClick={() => selectMode(m.key)}
                  className={`flex items-center gap-2.5 w-full px-3 py-2 text-sm text-left hover:bg-gray-50 transition-colors ${
                    mode === m.key
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-gray-700"
                  }`}
                >
                  {m.icon}
                  <span>{m.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Paste Console Panel — shown when paste button is clicked in debugger mode */}
      {showPastePanel && (
        <div className="px-3 py-2 border-b border-red-200 bg-red-50">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-red-700">
              Paste Console Error
            </span>
            <button
              onClick={() => { setShowPastePanel(false); setPasteContent(""); }}
              className="text-red-400 hover:text-red-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <textarea
            ref={pasteRef}
            value={pasteContent}
            onChange={(e) => setPasteContent(e.target.value)}
            placeholder="Paste browser console errors, stack traces, or error messages here..."
            rows={5}
            className="w-full px-2 py-1.5 text-xs font-mono bg-white border border-red-200 rounded resize-none focus:outline-none focus:ring-1 focus:ring-red-400"
          />
          <div className="flex justify-between items-center mt-1.5">
            <span className="text-[10px] text-red-400">
              Tip: Right-click an error in DevTools → Copy → Paste here
            </span>
            <button
              onClick={handlePasteSubmit}
              disabled={!pasteContent.trim() || isLoading}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Bug className="w-3 h-3" />
              Analyze
            </button>
          </div>
        </div>
      )}

      {/* Captured Errors Panel — auto-captured console.error / window errors */}
      {showCaptured && capturedErrors.length > 0 && (
        <div className="px-3 py-2 border-b border-orange-200 bg-orange-50 max-h-40 overflow-y-auto">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-orange-700">
              Captured Errors ({capturedErrors.length})
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => { clearErrors(); setShowCaptured(false); }}
                className="text-[10px] text-orange-400 hover:text-orange-600"
                title="Clear all"
              >
                Clear all
              </button>
              <button
                onClick={() => setShowCaptured(false)}
                className="text-orange-400 hover:text-orange-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <div className="space-y-1.5">
            {capturedErrors.slice(0, 10).map((err) => (
              <div
                key={err.id}
                className="flex items-start gap-1.5 p-1.5 bg-white border border-orange-200 rounded text-xs"
              >
                <AlertTriangle className="w-3 h-3 mt-0.5 text-orange-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-gray-700 truncate font-mono text-[10px]">
                    {err.message.slice(0, 120)}
                    {err.message.length > 120 ? "..." : ""}
                  </p>
                  <p className="text-[9px] text-gray-400 mt-0.5">
                    {err.type} · {formatDt(err.timestamp, 'datetime')}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => handleSendCaptured(err)}
                    disabled={isLoading}
                    className="px-1.5 py-0.5 text-[10px] font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    Debug
                  </button>
                  <button
                    onClick={() => clearError(err.id)}
                    className="text-gray-400 hover:text-red-500"
                    title="Dismiss"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm mt-8">
            <Bot className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-medium">CommerceExpert AI Assistant</p>
            <p className="mt-1 text-xs">{currentMode.placeholder}</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {MODES.filter((m) => m.key !== "general").map((m) => (
                <button
                  key={m.key}
                  onClick={() => selectMode(m.key)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {m.icon}
                  {m.shortLabel}
                </button>
              ))}
            </div>
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
                  ? `${currentMode.color} text-white`
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
                  {/* Mode badge on assistant messages */}
                  {msg.role === "assistant" && msg.mode && msg.mode !== "general" && (
                    <div className="text-xs text-gray-400 mb-1">
                      {MODES.find((m) => m.key === msg.mode)?.label ?? msg.mode}
                    </div>
                  )}

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
        {/* Console paste button — only in debugger mode */}
        {mode === "debugger" && (
          <button
            onClick={() => { setShowPastePanel(!showPastePanel); setShowCaptured(false); }}
            className={`p-2 rounded-lg transition-colors ${
              showPastePanel
                ? "bg-red-100 text-red-600"
                : "text-gray-400 hover:text-red-500 hover:bg-red-50"
            }`}
            title="Paste console error"
          >
            <ClipboardPaste className="w-4 h-4" />
          </button>
        )}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={currentMode.placeholder}
          disabled={isLoading}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className={`p-2 rounded-lg ${currentMode.color} text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default AiHelpWidget;
