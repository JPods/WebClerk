/**
 * athenaToken — frontend validation integrity proof.
 *
 * After envelope validation passes, the frontend computes
 * HMAC-SHA256(athena_key, serialized_body) and sends it as
 * X-Athena-Validated header. The backend verifies the HMAC —
 * proving the request went through legitimate frontend validation.
 *
 * The athena_key lives in the JWT access token claims (issued at login).
 * It is extracted by decoding the JWT payload (no signature verification
 * needed — the backend already verified the JWT via the Authorization header).
 *
 * Three outcomes on the backend:
 *   Token present + valid   → normal
 *   Token present + invalid → 400 reject (tampered)
 *   Token absent            → allowed but flagged (API client / curl)
 *
 * Established: 2026-09-02
 */

import { getAccessToken } from '../api/axios';

/**
 * Extract athena_key from the JWT access token claims.
 * Returns null if no token or no athena_key claim.
 */
export function getAthenaKey(): string | null {
  const token = getAccessToken();
  if (!token) return null;

  try {
    // JWT is three base64url segments — we want the payload (middle)
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.athena_key || null;
  } catch {
    return null;
  }
}

/**
 * Compute HMAC-SHA256 of serialized body using the athena_key.
 * Returns hex string, or null if no key available.
 *
 * Uses Web Crypto API (available in all modern browsers).
 */
export async function computeAthenaToken(body: string): Promise<string | null> {
  const key = getAthenaKey();
  if (!key) return null;

  try {
    const encoder = new TextEncoder();
    const cryptoKey = await crypto.subtle.importKey(
      'raw',
      encoder.encode(key),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign'],
    );
    const signature = await crypto.subtle.sign('HMAC', cryptoKey, encoder.encode(body));
    // Convert ArrayBuffer to hex string
    return Array.from(new Uint8Array(signature))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    return null;
  }
}
