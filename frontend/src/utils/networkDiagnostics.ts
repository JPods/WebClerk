/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Network Diagnostics Utility
 *
 * Helps diagnose network errors like ERR_NETWORK in Axios requests.
 * Use this to debug connectivity issues between frontend and backend.
 */

import { getAccessToken } from "../api/axios";

export interface DiagnosticReport {
  timestamp: string;
  frontend: {
    url: string;
    apiBaseUrl: string;
    environment: string;
    hasToken: boolean;
    tokenPrefix?: string;
  };
  backend: {
    isReachable: boolean;
    systemInfo?: any;
    cors: {
      preflight?: boolean;
      error?: string;
    };
  };
  recommendations: string[];
}

/**
 * Run full network diagnostics
 */
export async function runNetworkDiagnostics(
  apiBaseUrl: string,
): Promise<DiagnosticReport> {
  const recommendations: string[] = [];
  const report: DiagnosticReport = {
    timestamp: new Date().toISOString(),
    frontend: {
      url: window.location.href,
      apiBaseUrl: apiBaseUrl,
      environment: String(import.meta.env.VITE_ENV || "UNKNOWN"),
      hasToken: !!getAuthToken(),
      tokenPrefix: getAuthToken()?.substring(0, 20),
    },
    backend: {
      isReachable: false,
      cors: {},
    },
    recommendations: recommendations,
  };

  // Test 1: Check if backend is reachable
  try {
    const resp = await fetch(`${apiBaseUrl}/wcapi/system-info/`);
    report.backend.isReachable = resp.ok;
    if (resp.ok) {
      report.backend.systemInfo = await resp.json();
    } else {
      recommendations.push(
        `Backend returned ${resp.status}: ${resp.statusText}`,
      );
    }
  } catch (err) {
    recommendations.push(
      `❌ Cannot reach backend at ${apiBaseUrl}: ${String(err)}`,
    );
  }

  // Test 2: Check authentication token
  if (!report.frontend.hasToken) {
    recommendations.push(
      "❌ No authentication token found. You may not be logged in. " +
        "Try logging in first before accessing protected endpoints.",
    );
  }

  // Test 3: Check CORS preflight
  try {
    const preflightResp = await fetch(
      `${apiBaseUrl}/wcapi/get/?model_name=dashboard`,
      {
        method: "OPTIONS",
        headers: {
          "Access-Control-Request-Method": "GET",
          "Access-Control-Request-Headers": "content-type,authorization",
        },
      },
    );
    report.backend.cors.preflight = preflightResp.ok;
    if (!preflightResp.ok) {
      recommendations.push(
        `⚠️ CORS preflight failed (${preflightResp.status}). ` +
          `Server may not allow requests from ${window.location.origin}`,
      );
    }
  } catch (err) {
    report.backend.cors.error = String(err);
    recommendations.push(`⚠️ CORS preflight check failed: ${String(err)}`);
  }

  // Final recommendations
  if (!report.backend.isReachable && !report.frontend.hasToken) {
    recommendations.unshift("📋 Issues found:");
  }

  if (recommendations.length === 0) {
    recommendations.push(
      "✅ Network appears healthy. Issue may be elsewhere (check DevTools).",
    );
  }

  return report;
}

/**
 * Get the current authentication token
 */
function getAuthToken(): string | null {
  return getAccessToken();
}

/**
 * Log diagnostics to console in a readable format
 */
export async function logNetworkDiagnostics(apiBaseUrl: string) {
  const report = await runNetworkDiagnostics(apiBaseUrl);

  console.group("🔍 Network Diagnostics Report");
  console.table({
    Timestamp: report.timestamp,
    "Frontend URL": report.frontend.url,
    "API Base URL": report.frontend.apiBaseUrl,
    Environment: report.frontend.environment,
    Authenticated: report.frontend.hasToken ? "✅ Yes" : "❌ No",
    "Backend Reachable": report.backend.isReachable ? "✅ Yes" : "❌ No",
  });

  if (report.backend.systemInfo) {
    console.log("Backend System Info:", report.backend.systemInfo);
  }

  if (report.recommendations.length > 0) {
    console.group("Recommendations:");
    report.recommendations.forEach((rec) => console.log(rec));
    console.groupEnd();
  }

  console.groupEnd();

  return report;
}

/**
 * Format error for better debugging
 */
export function formatNetworkError(error: any): {
  code: string;
  message: string;
  status?: number;
  hint: string;
} {
  const code = error?.code || "UNKNOWN_ERROR";
  const message = error?.message || String(error);
  const status = error?.response?.status;

  let hint = "Unknown error";

  if (code === "ERR_NETWORK") {
    hint = "Network connection failed. Backend may be down or unreachable.";
  } else if (code === "ERR_BAD_RESPONSE") {
    hint = `Server returned ${status}. Check backend logs for details.`;
  } else if (status === 401) {
    hint = "Unauthorized. You may not be logged in or your token expired.";
  } else if (status === 403) {
    hint = "Forbidden. You may not have permission to access this resource.";
  } else if (status === 404) {
    hint = "Endpoint not found. The API route may have changed.";
  } else if (status === 500) {
    hint = "Server error. Check backend logs.";
  } else if (code === "ECONNABORTED") {
    hint = "Request timeout. Backend may be slow or unresponsive.";
  }

  return { code, message, status, hint };
}
