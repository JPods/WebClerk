/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * API Request Logger
 * 
 * Logs all R25 → WC3 API calls for debugging and auditing.
 * Sends log entries to the backend APILog model via /wcapi/log/api/
 */

import { AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';

// Generate unique correlation IDs to trace requests across systems
export const generateCorrelationId = (): string => {
  return `r25-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Configuration
const LOG_CONFIG = {
  // Enable/disable API logging (can be toggled via env var)
  enabled: import.meta.env.VITE_API_LOGGING !== 'false',
  // Log to console in development
  consoleLog: import.meta.env.DEV,
  // Send logs to backend
  sendToBackend: false,
  // Endpoints to skip logging (to avoid infinite loops)
  skipEndpoints: ['/wcapi/log/api/', '/api/token/refresh/'],
  // Max body size to log (truncate large payloads)
  maxBodySize: 10000,
};

interface APILogEntry {
  source: 'r25';
  destination: string;
  method: string;
  endpoint: string;
  request_headers?: Record<string, string>;
  request_body?: any;
  status_code?: number;
  response_headers?: Record<string, string>;
  response_body?: any;
  error_message?: string;
  duration_ms?: number;
  correlation_id: string;
  metadata?: Record<string, any>;
}

/**
 * Sanitize headers - remove sensitive values
 */
const sanitizeHeaders = (headers: any): Record<string, string> => {
  if (!headers) return {};
  const sanitized: Record<string, string> = {};
  const sensitiveKeys = ['authorization', 'cookie', 'x-api-key', 'token'];
  
  Object.entries(headers).forEach(([key, value]) => {
    if (sensitiveKeys.includes(key.toLowerCase())) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'string') {
      sanitized[key] = value;
    }
  });
  return sanitized;
};

/**
 * Truncate body if too large
 */
const truncateBody = (body: any): any => {
  if (!body) return body;
  const str = typeof body === 'string' ? body : JSON.stringify(body);
  if (str.length > LOG_CONFIG.maxBodySize) {
    return { _truncated: true, _size: str.length, _preview: str.substring(0, 500) };
  }
  return body;
};

/**
 * Check if this endpoint should be logged
 */
const shouldLog = (url: string): boolean => {
  if (!LOG_CONFIG.enabled) return false;
  return !LOG_CONFIG.skipEndpoints.some(skip => url.includes(skip));
};

/**
 * Mark request start time and add correlation ID
 */
export const onRequestStart = (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
  const correlationId = generateCorrelationId();
  (config as any)._correlationId = correlationId;
  (config as any)._startTime = Date.now();
  
  // Add correlation ID header so backend can link logs
  config.headers = config.headers || {};
  config.headers['X-Correlation-ID'] = correlationId;
  
  return config;
};

/**
 * Log successful response
 */
export const onResponseSuccess = async (response: AxiosResponse): Promise<AxiosResponse> => {
  const config = response.config as any;
  const url = config.url || '';
  
  if (!shouldLog(url)) return response;
  
  const correlationId = config._correlationId || 'unknown';
  const startTime = config._startTime;
  const duration = startTime ? Date.now() - startTime : undefined;
  
  const logEntry: APILogEntry = {
    source: 'r25',
    destination: 'wc3',
    method: (config.method || 'GET').toUpperCase(),
    endpoint: url,
    request_headers: sanitizeHeaders(config.headers),
    request_body: truncateBody(config.data),
    status_code: response.status,
    response_headers: sanitizeHeaders(response.headers),
    response_body: truncateBody(response.data),
    duration_ms: duration,
    correlation_id: correlationId,
  };
  
  // Console log in dev
  if (LOG_CONFIG.consoleLog) {
    console.log(
      `%c[API] ${logEntry.method} ${logEntry.endpoint} → ${logEntry.status_code} (${duration}ms)`,
      'color: #22c55e'
    );
  }
  
  // Send to backend (async, don't block response)
  // Backend logging disabled
  
  return response;
};

/**
 * Log failed response
 */
export const onResponseError = async (error: AxiosError): Promise<never> => {
  const config = error.config as any;
  const url = config?.url || '';
  
  if (config && shouldLog(url)) {
    const correlationId = config._correlationId || 'unknown';
    const startTime = config._startTime;
    const duration = startTime ? Date.now() - startTime : undefined;
    
    const logEntry: APILogEntry = {
      source: 'r25',
      destination: 'wc3',
      method: (config.method || 'GET').toUpperCase(),
      endpoint: url,
      request_headers: sanitizeHeaders(config.headers),
      request_body: truncateBody(config.data),
      status_code: error.response?.status,
      response_headers: sanitizeHeaders(error.response?.headers),
      response_body: truncateBody(error.response?.data),
      error_message: error.message,
      duration_ms: duration,
      correlation_id: correlationId,
    };
    
    // Console log in dev
    if (LOG_CONFIG.consoleLog) {
      console.log(
        `%c[API] ${logEntry.method} ${logEntry.endpoint} → ${logEntry.status_code || 'ERR'} (${duration}ms) - ${error.message}`,
        'color: #ef4444'
      );
    }
    
    // Send to backend
    // Backend logging disabled
  }
  
  return Promise.reject(error);
};

/**
 * Send log entry to backend
 */
const sendLogToBackend = async (entry: APILogEntry): Promise<void> => {
  // Use fetch directly to avoid interceptor loops
  // Disabled
  return Promise.resolve();
};

/**
 * Manually log an API call (for non-axios requests)
 */
export const logAPICall = (entry: Partial<APILogEntry>): void => {
  if (!LOG_CONFIG.enabled) return;
  
  const fullEntry: APILogEntry = {
    source: 'r25',
    destination: 'wc3',
    method: 'GET',
    endpoint: '',
    correlation_id: generateCorrelationId(),
    ...entry,
  };
  
  if (LOG_CONFIG.consoleLog) {
    const color = (fullEntry.status_code && fullEntry.status_code >= 400) ? '#ef4444' : '#22c55e';
    console.log(
      `%c[API] ${fullEntry.method} ${fullEntry.endpoint} → ${fullEntry.status_code || 'N/A'}`,
      `color: ${color}`
    );
  }
  
  if (LOG_CONFIG.sendToBackend) {
    sendLogToBackend(fullEntry).catch(() => {});
  }
};
