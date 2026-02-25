/**
 * Render Metrics Types
 *
 * TypeScript interfaces matching the backend RenderMetricsCollector.get_snapshot() output.
 * Streamed via Socket.IO /metrics namespace at 1 Hz.
 */

/** FPS measurements */
export interface FpsMetrics {
  actual: number;
}

/** Pipeline stage timing (milliseconds) */
export interface PipelineMetrics {
  build_avg_ms: number;
  merge_avg_ms: number;
  write_to_hardware_avg_ms: number;
  emit_avg_ms: number;
  render_cycle_avg_ms: number;

  build_max_ms: number;
  merge_max_ms: number;
  write_to_hardware_max_ms: number;
  emit_max_ms: number;
  render_cycle_max_ms: number;

  /** Last 60 samples for sparkline charts */
  build_history: number[];
  write_to_hardware_history: number[];
  render_cycle_history: number[];
}

/** Global frame counters */
export interface CounterMetrics {
  frames_rendered: number;
  dma_skipped: number;
  frames_expired: number;
  frames_submitted: number;
  /** dma_skipped / (frames_rendered + dma_skipped) */
  redundant_ratio: number;
}

/** Per-zone metrics */
export interface ZoneMetricsData {
  produced: number;
  rendered: number;
  expired: number;
  change_count: number;
  static_count: number;
  change_ratio: number;
  last_source: string | null;
}

/** Per-animation metrics */
export interface AnimationMetricsData {
  frames_produced: number;
  avg_step_ms: number;
  max_step_ms: number;
}

/** Complete snapshot emitted by MetricsStreamer */
export interface RenderMetricsSnapshot {
  fps: FpsMetrics;
  pipeline: PipelineMetrics;
  counters: CounterMetrics;
  zones: Record<string, ZoneMetricsData>;
  animations: Record<string, AnimationMetricsData>;
  timestamp: number;
}
