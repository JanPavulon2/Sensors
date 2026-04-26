import { useFrameMetrics } from '../realtime/frames.store';

export function FrameMetadata() {
  const { fps, frameCount } = useFrameMetrics();

  return (
    <div className="flex gap-4 text-sm text-text-secondary">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" />
        <span>Live</span>
      </div>
      <div>FPS: <span className="font-mono">{fps}</span></div>
      <div>Frames: <span className="font-mono">{frameCount}</span></div>
    </div>
  );
}
