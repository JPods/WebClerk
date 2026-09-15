/**
 * Test factories for WebClerk API envelope responses.
 *
 * Every wcapi response is an ApiEnvelope. Tests should construct
 * responses with these factories — never use raw objects.
 */
import type { ApiEnvelope } from '@/api/wcapi';

/**
 * Build a success envelope wrapping the given data.
 */
export function buildEnvelope<T>(data: T, overrides?: Partial<ApiEnvelope<T>>): ApiEnvelope<T> {
  return {
    status: 'success',
    code: 200,
    message: '',
    data,
    error: null,
    ...overrides,
  };
}

/**
 * Build an error envelope.
 */
export function buildErrorEnvelope(
  message: string,
  error: Record<string, unknown> = {},
  code = 400,
): ApiEnvelope<null> {
  return {
    status: 'error',
    code,
    message,
    data: null,
    error,
  };
}

/**
 * Build a list response envelope (wcapi/get/ pattern).
 */
export function buildListEnvelope<T>(
  results: T[],
  overrides?: { total?: number; model_name?: string },
): ApiEnvelope<{ results: T[]; total: number; model_name?: string }> {
  return buildEnvelope({
    results,
    total: overrides?.total ?? results.length,
    model_name: overrides?.model_name,
  });
}
