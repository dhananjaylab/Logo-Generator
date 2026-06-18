'use client';

/**
 * AuthContext — in-memory authentication token provider.
 *
 * SECURITY FIX (P1.1 / VULN-01):
 * Replaces the previous pattern of storing JWTs in localStorage (XSS risk)
 * and reading tokens from NEXT_PUBLIC_ env vars (baked into the JS bundle).
 *
 * How it works:
 *  1. On mount, AuthProvider fetches the token from the server-side
 *     Next.js route /api/auth/token (which reads server-only env vars).
 *  2. The token lives exclusively in React state — process memory only.
 *  3. If the tab is closed or the page reloads, a fresh token is fetched.
 *  4. No localStorage, no sessionStorage, no cookies containing raw tokens.
 *
 * All components that need the token call useAuth() instead of reading
 * localStorage or environment variables.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';

interface AuthContextValue {
  /** The current bearer token, or null while loading / unauthenticated. */
  token: string | null;
  /** True while the initial token fetch is in progress. */
  loading: boolean;
  /** Human-readable auth error, if any. */
  error: string | null;
  /** Re-fetch the token (e.g. after a 401 response). */
  refresh: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  token: null,
  loading: true,
  error: null,
  refresh: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken]   = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  const fetchToken = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/auth/token', { credentials: 'same-origin' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error ?? `Auth failed (${res.status})`);
      }
      const { token: t } = await res.json();
      if (!t || typeof t !== 'string') throw new Error('Server returned no token');
      setToken(t);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication error';
      console.error('[AuthContext]', msg);
      setError(msg);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch once on mount.
  useEffect(() => { fetchToken(); }, [fetchToken]);

  return (
    <AuthContext.Provider value={{ token, loading, error, refresh: fetchToken }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Hook — consume inside any component wrapped by AuthProvider. */
export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
