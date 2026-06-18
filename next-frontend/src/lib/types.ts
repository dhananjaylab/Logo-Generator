/**
 * TypeScript type definitions for Logo Generator API.
 *
 * SECURITY FIX (P1.6): HistoryEntry no longer includes ip_address or user_id.
 * The backend HistoryEntryResponse model explicitly excludes those fields, and
 * the frontend type mirrors that contract so no accidental rendering or logging
 * of sensitive data can occur client-side.
 */

export interface LogoGenerationResponse {
  result: string[];
  generator: string;
  prompt: string;
  brand: string;
  style: string;
  palette: string;
  status?: 'completed' | 'failed';
}

export interface JobStatusResponse {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  result?: LogoGenerationResponse;
  error?: string;
}

/**
 * Safe public representation of a generation history record.
 * Matches backend HistoryEntryResponse — ip_address and user_id are
 * intentionally absent.
 */
export interface HistoryEntry {
  id: number;
  brand_name: string;
  prompt: string;
  generator: string;
  created_at: string;
  image_url: string;
}

export interface LogoGenerationRequest {
  text: string;
  description: string;
  generator: 'gpt-image-2-2026-04-21' | 'gemini';
  style: string;
  palette: string;
  tagline?: string;
  typography?: string;
  elem_include?: string;
  elem_avoid?: string;
  mission?: string;
}

/** Response from POST /api/v1/ws/ticket — used by the frontend before opening a WebSocket. */
export interface WsTicketResponse {
  ticket: string;
  expires_in: number;
}
