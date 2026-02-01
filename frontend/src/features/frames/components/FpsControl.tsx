import { useState } from 'react';
import { Slider } from '@/shared/ui/slider';

interface FpsControlProps {
  initialFps?: number;
  onFpsChange?: (fps: number) => void;
}

export function FpsControl({ initialFps = 30, onFpsChange }: FpsControlProps) {
  const [fps, setFps] = useState(initialFps);

  const handleFpsChange = (value: number[]) => {
    const newFps = value[0];
    setFps(newFps);
    onFpsChange?.(newFps);
  };

  return (
    <div className="flex items-center gap-3 min-w-[200px]">
      <span className="text-sm text-text-secondary whitespace-nowrap">Stream FPS:</span>
      <div className="flex-1">
        <Slider
          value={[fps]}
          onValueChange={handleFpsChange}
          min={5}
          max={60}
          step={5}
          className="w-full"
        />
      </div>
      <span className="text-sm font-mono font-medium w-8 text-right">{fps}</span>
    </div>
  );
}
