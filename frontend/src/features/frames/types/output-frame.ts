export type RGB = [number, number, number];

export interface OutputFrame {
  t: number;  // Global animation time
  zones: Record<string, RGB[]>;  // Zone ID → pixels
}

export interface FrameMetrics {
  fps: number;
  latency: number;
  frameCount: number;
  lastFrameTime: number;
}
