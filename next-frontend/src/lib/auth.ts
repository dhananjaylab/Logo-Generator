/**
 * Authentication and API configuration utilities.
 *
 * SECURITY FIX (P1.1 / VULN-01):
 * All localStorage-based token storage has been removed. Storing JWTs in
 * localStorage exposes them to XSS attacks — any injected script (malicious
 * npm package, browser extension, etc.) can read localStorage and exfiltrate
 * the token.
 *
 * Tokens are now held exclusively in React component memory via AuthContext
 * (src/contexts/AuthContext.tsx), which fetches them from a server-side
 * Next.js API route (/api/auth/token) that reads server-only env vars.
 *
 * SECURITY FIX (P1.1 / VULN-01):
 * NEXT_PUBLIC_DEV_TOKEN and NEXT_PUBLIC_JWT_TOKEN have been removed entirely.
 * Public Next.js env vars are baked into the JavaScript bundle and served to
 * every visitor, making any token value effectively public. Token provisioning
 * now happens server-side only via /api/auth/token.
 */

/**
 * Get the REST API base URL.
 * NEXT_PUBLIC_API_URL is safe to expose — it is an endpoint address, not a credential.
 */
export function getApiUrl(): string {
  const base = (
    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  ).replace(/\/$/, '');
  return base.endsWith('/api/v1') ? base : `${base}/api/v1`;
}

/**
 * Derive the WebSocket URL from the API URL.
 */
export function getWsUrl(): string {
  const apiUrl = getApiUrl();
  if (apiUrl.startsWith('https://')) return apiUrl.replace('https://', 'wss://');
  if (apiUrl.startsWith('http://'))  return apiUrl.replace('http://', 'ws://');
  return apiUrl;
}

/**
 * Fetch wrapper that attaches the Authorization Bearer header.
 *
 * The `token` parameter is required and must come from AuthContext — there is
 * no localStorage or env-var fallback. If token is null the request is sent
 * without an Authorization header, which the backend will reject with 401.
 */
export async function authenticatedFetch(
  url: string,
  options?: RequestInit,
  token?: string | null,
): Promise<Response> {
  const headers = new Headers(options?.headers ?? {});
  headers.set('Content-Type', 'application/json');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(url, { ...options, headers });
}
