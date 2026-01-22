/**
 * Data Set Identification Utility
 *
 * Helps verify that frontend and backend are connected to the same data set.
 * Use this to prevent accidentally mixing DEV/STAGING/PRODUCTION data.
 */

export interface DataSetInfo {
  id: string;
  name: string;
}

export interface SystemInfo {
  data_set: DataSetInfo;
  database: {
    host: string;
    name: string;
  };
  server: {
    debug: boolean;
    django_version: number[];
    python_version: string;
  };
  message: string;
}

/**
 * Get frontend data set configuration from environment variables
 */
export function getFrontendDataSet(): DataSetInfo {
  return {
    id: String(import.meta.env.VITE_DATA_SET_ID || "UNKNOWN").replace(
      /['"]/g,
      "",
    ),
    name: String(import.meta.env.VITE_DATA_SET_NAME || "Unknown").replace(
      /['"]/g,
      "",
    ),
  };
}

/**
 * Fetch backend system info including data set identification
 */
export async function fetchBackendSystemInfo(
  apiBaseUrl: string = "",
): Promise<SystemInfo> {
  const url = `${apiBaseUrl}/wcapi/get/?model_name=system_info`;
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch system info: ${response.status}`);
  }

  const json = await response.json();

  // Unwrap envelope if present (AutoEnvelopeMiddleware wraps responses)
  if (json.data && typeof json.data === "object" && json.data.data_set) {
    return json.data;
  }

  return json;
}

/**
 * Check if frontend and backend data sets match
 */
export function validateDataSetMatch(
  frontend: DataSetInfo,
  backend: DataSetInfo,
): { isMatch: boolean; message: string } {
  const isMatch = frontend.id === backend.id;

  if (isMatch) {
    return {
      isMatch: true,
      message: `✓ Data sets match: ${frontend.id} (${frontend.name})`,
    };
  }

  return {
    isMatch: false,
    message: `⚠️ DATA SET MISMATCH! Frontend: ${frontend.id} (${frontend.name}) vs Backend: ${backend.id} (${backend.name})`,
  };
}

/**
 * Log data set info to console (useful for debugging)
 */
export function logDataSetInfo(
  frontend: DataSetInfo,
  backend?: SystemInfo,
): void {
  console.group("🔍 Data Set Identification");
  console.log("Frontend:", frontend.id, "-", frontend.name);

  if (backend?.data_set) {
    console.log("Backend:", backend.data_set.id, "-", backend.data_set.name);
    console.log(
      "Database:",
      backend.database?.name ?? "N/A",
      "@",
      backend.database?.host ?? "N/A",
    );
    console.log("Server Debug:", backend.server?.debug ?? "N/A");

    const validation = validateDataSetMatch(frontend, backend.data_set);
    if (validation.isMatch) {
      console.log("%c" + validation.message, "color: green; font-weight: bold");
    } else {
      console.warn(validation.message);
    }
  } else if (backend) {
    console.warn("Backend responded but data_set is missing from response");
  }

  console.groupEnd();
}
