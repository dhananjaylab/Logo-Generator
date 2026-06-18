/**
 * Server-side authentication token endpoint.
 *
 * SECURITY FIX (P1.1 / VULN-01):
 * This Next.js API route runs exclusively on the server. It reads DEV_TOKEN
 * from process.env (a server-only variable, NOT prefixed NEXT_PUBLIC_), so the
 * token value is never included in the JavaScript bundle sent to browsers.
 *
 * The browser-side AuthContext calls this endpoint once on mount and holds the
 * token in React state (memory only). No localStorage, no sessionStorage,
 * no cookies containing the raw JWT.
 *
 * Production path (Clerk):
 * Uncomment the Clerk block below after installing @clerk/nextjs. The SDK reads
 * the session cookie set by Clerk's middleware and returns a short-lived token
 * without the browser ever seeing the underlying session secret.
 */

import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest): Promise<NextResponse> {
  const env = process.env.ENV ?? process.env.NODE_ENV ?? 'development';
  const isProduction = env === 'production' || env === 'staging';

  // ── Development bypass ───────────────────────────────────────────────────
  // DEV_TOKEN is a server-only env var (no NEXT_PUBLIC_ prefix).
  // ALLOW_DEV_TOKEN must be explicitly "true" and the env must not be prod/staging.
  const devToken = process.env.DEV_TOKEN;
  const allowDevToken = process.env.ALLOW_DEV_TOKEN === 'true';

  if (!isProduction && allowDevToken && devToken) {
    return NextResponse.json({ token: devToken });
  }

  // ── Production: Clerk server-side session ────────────────────────────────
  // Uncomment after: npm install @clerk/nextjs
  //
  // import { auth } from '@clerk/nextjs/server';
  //
  // const { getToken } = auth();
  // const token = await getToken();
  // if (!token) {
  //   return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  // }
  // return NextResponse.json({ token });

  return NextResponse.json(
    {
      error:
        'Authentication not configured. ' +
        'Set ALLOW_DEV_TOKEN=true + DEV_TOKEN in your local .env, ' +
        'or integrate @clerk/nextjs for production.',
    },
    { status: 401 },
  );
}
