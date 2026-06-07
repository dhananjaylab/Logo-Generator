/**
 * TypeScript type definitions for Logo Generator API
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

export interface HistoryEntry {
  id: number;
  brand_name: string;
  prompt: string;
  generator: string;
  created_at: string;
  image_url: string;
  user_id?: string | null;
  ip_address?: string | null;
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
