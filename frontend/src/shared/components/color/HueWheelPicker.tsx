/**
 * Hue Wheel Picker - Canvas-based 360° color wheel
 *
 * Features:
 * - Smooth 360° hue spectrum gradient
 * - Mouse/touch interaction with drag support
 * - Visual indicator of current hue with glow effect
 * - High-performance canvas rendering
 */

import React, { useRef, useEffect, useCallback, useState } from 'react';

interface HueWheelPickerProps {
  hue: number;
  onChange: (hue: number) => void;
  compact?: boolean;
  disabled?: boolean;
}

/**
 * HueWheelPicker Component
 * Canvas-based color wheel for intuitive hue selection
 */
export const HueWheelPicker: React.FC<HueWheelPickerProps> = ({
  hue,
  onChange,
  compact = false,
  disabled = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const pendingHueRef = useRef<number | null>(null);
  const rafIdRef = useRef<number | null>(null);

  // Render wheel
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 10;

    // Clear canvas
    ctx.fillStyle = 'rgba(10, 14, 20, 0.95)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw hue wheel
    for (let angle = 0; angle < 360; angle += 2) {
      const rad = ((angle - 90) * Math.PI) / 180;
      const x1 = centerX + Math.cos(rad) * (radius * 0.4);
      const y1 = centerY + Math.sin(rad) * (radius * 0.4);
      const x2 = centerX + Math.cos(rad) * radius;
      const y2 = centerY + Math.sin(rad) * radius;

      // Create color from hue
      const hsvColor = hslToRGB(angle, 100, 50);
      ctx.strokeStyle = `rgb(${hsvColor[0]}, ${hsvColor[1]}, ${hsvColor[2]})`;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }

    // Draw center circle with glow
    ctx.fillStyle = 'rgba(20, 25, 35, 0.9)';
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.3, 0, Math.PI * 2);
    ctx.fill();

    // Draw current hue indicator
    const currentRad = ((hue - 90) * Math.PI) / 180;
    const indicatorX = centerX + Math.cos(currentRad) * radius;
    const indicatorY = centerY + Math.sin(currentRad) * radius;

    // Outer glow
    ctx.fillStyle = 'rgba(0, 255, 0, 0.3)';
    ctx.beginPath();
    ctx.arc(indicatorX, indicatorY, 16, 0, Math.PI * 2);
    ctx.fill();

    // Indicator dot
    const indicatorColor = hslToRGB(hue, 100, 50);
    ctx.fillStyle = `rgb(${indicatorColor[0]}, ${indicatorColor[1]}, ${indicatorColor[2]})`;
    ctx.beginPath();
    ctx.arc(indicatorX, indicatorY, 10, 0, Math.PI * 2);
    ctx.fill();

    // White border on indicator
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw hue value in center
    ctx.fillStyle = 'rgba(232, 234, 237, 0.8)';
    ctx.font = 'bold 20px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${Math.round(hue)}°`, centerX, centerY);
  }, [hue]);

  // Calculate hue from mouse position
  const calculateHueFromEvent = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    const angle = Math.atan2(y - centerY, x - centerX);
    const hueValue = (angle * 180) / Math.PI + 90;
    return ((hueValue % 360) + 360) % 360;
  }, []);

  // Throttled update during drag using RAF
  const updateHueThrottled = useCallback((newHue: number) => {
    pendingHueRef.current = newHue;

    if (rafIdRef.current === null) {
      rafIdRef.current = requestAnimationFrame(() => {
        if (pendingHueRef.current !== null) {
          onChange(pendingHueRef.current);
        }
        rafIdRef.current = null;
      });
    }
  }, [onChange]);

  // Handle clicks on wheel
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (disabled) return;
      const newHue = calculateHueFromEvent(e);
      if (newHue !== null) {
        onChange(newHue);
      }
    },
    [calculateHueFromEvent, onChange, disabled]
  );

  // Handle mouse down for dragging
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (disabled) return;
    setIsDragging(true);
    handleCanvasClick(e);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging || disabled) return;
    const newHue = calculateHueFromEvent(e);
    if (newHue !== null) {
      updateHueThrottled(newHue);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    // Flush any pending update
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
    if (pendingHueRef.current !== null) {
      onChange(pendingHueRef.current);
      pendingHueRef.current = null;
    }
  };

  const size = compact ? 140 : 280;

  return (
    <div className="flex flex-col items-center gap-2">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        className={`rounded-lg border border-border-default transition-opacity ${
          disabled ? 'opacity-50 cursor-not-allowed' : ''
        }`}
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: disabled ? 'not-allowed' : 'crosshair' }}
      />
      <p className="text-xs text-text-tertiary hidden">← Click or drag to select hue →</p>
    </div>
  );
};

/**
 * Convert HSL to RGB
 * Used for drawing the color wheel
 */
function hslToRGB(h: number, s: number, l: number): [number, number, number] {
  const hh = h / 360;
  const ss = s / 100;
  const ll = l / 100;

  let r, g, b;

  if (ss === 0) {
    r = g = b = ll;
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    const q = ll < 0.5 ? ll * (1 + ss) : ll + ss - ll * ss;
    const p = 2 * ll - q;
    r = hue2rgb(p, q, hh + 1 / 3);
    g = hue2rgb(p, q, hh);
    b = hue2rgb(p, q, hh - 1 / 3);
  }

  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

export default HueWheelPicker;
