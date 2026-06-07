/**
 * TypeScript type definitions for Logo Generator API
 */

export interface LogoGenerationResponse {
  request_id: string;
  brand_name: string;
  style: string;
  palette: string;
  description: string;
  generator: string;
  created_at: string;
  status: 'processing' | 'completed' | 'failed';
  variations: string[];
  timestamp?: number;
}

export interface JobStatusResponse {
  request_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: LogoGenerationResponse;
  error?: string;
}

export interface HistoryEntry {
  request_id: string;
  brand_name: string;
  style: string;
  palette: string;
  generator: string;
  created_at: string;
  variations: string[];
  status: 'completed' | 'failed';
  thumbnail?: string;
}

export interface LogoGenerationRequest {
  brand_name: string;
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
