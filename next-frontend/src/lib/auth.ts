/**
 * Authentication and API configuration utilities
 * Client-side only - runs in browser, not during SSR
 */

/**
 * Get authentication token from localStorage or environment
 * Uses DEV_TOKEN for development, expects Clerk token in production
 */
export async function getAuthToken(): Promise<string> {
  // Only run on client side
  if (typeof window === 'undefined') {
    throw new Error('getAuthToken() can only be called from the browser');
  }

  // Check if token is cached in localStorage
  const cachedToken = localStorage.getItem('auth_token');
  if (cachedToken) {
    return cachedToken;
  }

  // For development, use the DEV_TOKEN from environment
  const devToken = process.env.NEXT_PUBLIC_DEV_TOKEN;
  if (devToken) {
    localStorage.setItem('auth_token', devToken);
    console.log('[Auth] Using DEV_TOKEN from environment');
    return devToken;
  }

  // For production, expect a Clerk token
  const clerkToken = process.env.NEXT_PUBLIC_JWT_TOKEN;
  if (clerkToken) {
    localStorage.setItem('auth_token', clerkToken);
    return clerkToken;
  }

  throw new Error(
    'No authentication token available. ' +
    'Set NEXT_PUBLIC_DEV_TOKEN for development or NEXT_PUBLIC_JWT_TOKEN for production'
  );
}

/**
 * Get the API base URL
 */
export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

/**
 * Get the WebSocket URL for the API
 */
export function getWsUrl(): string {
  const apiUrl = getApiUrl();
  // Convert http(s) to ws(s)
  if (apiUrl.startsWith('https://')) {
    return apiUrl.replace('https://', 'wss://');
  }
  if (apiUrl.startsWith('http://')) {
    return apiUrl.replace('http://', 'ws://');
  }
  return apiUrl;
}

/**
 * Fetch with authentication header
 * Should be called from client-side code only
 */
export async function authenticatedFetch(
  url: string,
  options?: RequestInit,
  token?: string | null
): Promise<Response> {
  // Get token from parameter, localStorage, or environment
  let authToken = token;
  
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('auth_token');
  }
  
  if (!authToken) {
    authToken = process.env.NEXT_PUBLIC_DEV_TOKEN || process.env.NEXT_PUBLIC_JWT_TOKEN;
  }

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  return fetch(url, {
    ...options,
    headers,
  });
}
