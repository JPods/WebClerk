/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { FaTimes, FaCopy, FaCheck } from "react-icons/fa";
import { useState } from "react";
import Badge from "@/components/ui/badge/Badge";
import { DevBadge } from "@/components/common/DevBadge";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface APILogRecord {
  id: number;
  source: string;
  destination: string;
  method: string;
  endpoint: string;
  request_headers?: Record<string, string>;
  request_body?: any;
  status_code: number | null;
  response_headers?: Record<string, string>;
  response_body?: any;
  error_message: string;
  duration_ms: number | null;
  correlation_id: string;
  ip_address?: string;
  metadata?: Record<string, any>;
  dt_created: string;
  user_id?: number;
}

interface APILogDetailProps {
  log: APILogRecord;
  onClose: () => void;
}

function APILogDetail({ log, onClose }: APILogDetailProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"request" | "response">("request");

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const formatJson = (data: any) => {
    if (!data || Object.keys(data).length === 0) return "{}";
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getStatusBadge = (statusCode: number | null) => {
    if (!statusCode) return <Badge color="light">N/A</Badge>;
    if (statusCode >= 200 && statusCode < 300) {
      return <Badge color="success">{statusCode} OK</Badge>;
    } else if (statusCode >= 400 && statusCode < 500) {
      return <Badge color="warning">{statusCode} Client Error</Badge>;
    } else if (statusCode >= 500) {
      return <Badge color="error">{statusCode} Server Error</Badge>;
    }
    return <Badge color="info">{statusCode}</Badge>;
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case "r25":
        return "React2025 Frontend";
      case "wc3":
        return "WebClerk3 Backend";
      case "ext":
        return "External Service";
      default:
        return source;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              <DevBadge label="APILogDetail" className="mr-2" />
              API Log Details
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {formatDate(log.dt_created)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full"
          >
            <FaTimes className="text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Summary Section */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Source
              </label>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {getSourceLabel(log.source)}
              </p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Destination
              </label>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {log.destination}
              </p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Status
              </label>
              <div className="mt-1">{getStatusBadge(log.status_code)}</div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Duration
              </label>
              <p className={`text-sm font-medium ${(log.duration_ms || 0) > 1000 ? "text-red-500" : "text-gray-900 dark:text-white"}`}>
                {log.duration_ms ? `${log.duration_ms}ms` : "-"}
              </p>
            </div>
          </div>

          {/* Method & Endpoint */}
          <div className="mb-6">
            <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              Request
            </label>
            <div className="flex items-center gap-2 mt-1 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <Badge
                color={
                  log.method === "GET"
                    ? "success"
                    : log.method === "POST"
                    ? "primary"
                    : log.method === "DELETE"
                    ? "error"
                    : "warning"
                }
              >
                {log.method}
              </Badge>
              <code className="text-sm font-mono text-gray-800 dark:text-gray-200 flex-1 truncate">
                {log.endpoint}
              </code>
              <button
                onClick={() => copyToClipboard(log.endpoint, "endpoint")}
                className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                title="Copy endpoint"
              >
                {copiedField === "endpoint" ? (
                  <FaCheck className="text-green-500" size={12} />
                ) : (
                  <FaCopy className="text-gray-400" size={12} />
                )}
              </button>
            </div>
          </div>

          {/* Correlation ID */}
          {log.correlation_id && (
            <div className="mb-6">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Correlation ID
              </label>
              <div className="flex items-center gap-2 mt-1">
                <code className="text-xs font-mono text-gray-600 dark:text-gray-400">
                  {log.correlation_id}
                </code>
                <button
                  onClick={() => copyToClipboard(log.correlation_id, "correlation")}
                  className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                >
                  {copiedField === "correlation" ? (
                    <FaCheck className="text-green-500" size={10} />
                  ) : (
                    <FaCopy className="text-gray-400" size={10} />
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Error Message */}
          {log.error_message && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <label className="text-xs font-medium text-red-600 dark:text-red-400 uppercase">
                Error Message
              </label>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                {log.error_message}
              </p>
            </div>
          )}

          {/* Request/Response Tabs */}
          <div className="border-b dark:border-gray-700 mb-4">
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab("request")}
                className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "request"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                }`}
              >
                Request
              </button>
              <button
                onClick={() => setActiveTab("response")}
                className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "response"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                }`}
              >
                Response
              </button>
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === "request" && (
            <div className="space-y-4">
              {/* Request Headers */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Headers
                  </label>
                  <button
                    onClick={() =>
                      copyToClipboard(formatJson(log.request_headers), "req_headers")
                    }
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                  >
                    {copiedField === "req_headers" ? (
                      <>
                        <FaCheck size={10} /> Copied
                      </>
                    ) : (
                      <>
                        <FaCopy size={10} /> Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto max-h-40">
                  {formatJson(log.request_headers)}
                </pre>
              </div>

              {/* Request Body */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Body
                  </label>
                  <button
                    onClick={() =>
                      copyToClipboard(formatJson(log.request_body), "req_body")
                    }
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                  >
                    {copiedField === "req_body" ? (
                      <>
                        <FaCheck size={10} /> Copied
                      </>
                    ) : (
                      <>
                        <FaCopy size={10} /> Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto max-h-60">
                  {formatJson(log.request_body)}
                </pre>
              </div>
            </div>
          )}

          {activeTab === "response" && (
            <div className="space-y-4">
              {/* Response Headers */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Headers
                  </label>
                  <button
                    onClick={() =>
                      copyToClipboard(formatJson(log.response_headers), "res_headers")
                    }
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                  >
                    {copiedField === "res_headers" ? (
                      <>
                        <FaCheck size={10} /> Copied
                      </>
                    ) : (
                      <>
                        <FaCopy size={10} /> Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto max-h-40">
                  {formatJson(log.response_headers)}
                </pre>
              </div>

              {/* Response Body */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Body
                  </label>
                  <button
                    onClick={() =>
                      copyToClipboard(formatJson(log.response_body), "res_body")
                    }
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                  >
                    {copiedField === "res_body" ? (
                      <>
                        <FaCheck size={10} /> Copied
                      </>
                    ) : (
                      <>
                        <FaCopy size={10} /> Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto max-h-60">
                  {formatJson(log.response_body)}
                </pre>
              </div>
            </div>
          )}

          {/* Metadata */}
          {log.metadata && Object.keys(log.metadata).length > 0 && (
            <div className="mt-6">
              <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Metadata
              </label>
              <pre className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto">
                {formatJson(log.metadata)}
              </pre>
            </div>
          )}

          {/* Additional Info */}
          <div className="mt-6 pt-4 border-t dark:border-gray-700 grid grid-cols-2 gap-4 text-xs text-gray-500 dark:text-gray-400">
            <div>
              <span className="font-medium">Log ID:</span> {log.id}
            </div>
            {log.ip_address && (
              <div>
                <span className="font-medium">IP Address:</span> {log.ip_address}
              </div>
            )}
            {log.user_id && (
              <div>
                <span className="font-medium">User ID:</span> {log.user_id}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default withDevIdentifier(APILogDetail, 'APILogDetail');
