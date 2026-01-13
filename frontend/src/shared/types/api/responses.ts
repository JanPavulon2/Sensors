/**
 * API Response Types
 * Defines API response structures
 */

export interface ApiError {
  status: number;
  message: string;
  details?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SystemStatus {
  connected: boolean;
  fps: number;
  power_draw: number; // watts
  uptime: number; // seconds
  mode: string;
  temperature?: number;
}
