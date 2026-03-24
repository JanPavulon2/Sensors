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
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const pendingHueRef = useRef<number | null>(null);
  const rafIdRef = useRef<number | null>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 280, height: 280 });

  // Responsive sizing: use container width up to max, or min for compact
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateSize = () => {
      const width = container.clientWidth;
      const height = container.clientHeight;

      // Use container size, minimum 140px for compact, 240px for full
      const size = Math.max(compact ? 140 : 240, Math.min(width, height));
      setCanvasSize({ width: size, height: size });
    };

    updateSize();

    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(container);

    return () => resizeObserver.disconnect();
  }, [compact]);

  // Render wheel with device pixel ratio for crisp rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas resolution for high DPI displays
    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasSize.width * dpr;
    canvas.height = canvasSize.height * dpr;
    ctx.scale(dpr, dpr);

    const centerX = canvasSize.width / 2;
    const centerY = canvasSize.height / 2;
    const radius = Math.min(centerX, centerY) - 10;
    const innerRadius = radius * 0.35;

    // Clear canvas with transparent background
    ctx.fillStyle = 'rgba(0, 0, 0, 0)';
    ctx.clearRect(0, 0, canvasSize.width, canvasSize.height);

    // Draw hue wheel as smooth gradient segments (no dark spots)
    for (let angle = 0; angle < 360; angle++) {
      const rad = ((angle - 90) * Math.PI) / 180;
      const nextRad = ((angle + 1 - 90) * Math.PI) / 180;

      // Create gradient for smooth color transition
      const gradient = ctx.createLinearGradient(
        centerX + Math.cos(rad) * innerRadius,
        centerY + Math.sin(rad) * innerRadius,
        centerX + Math.cos(rad) * radius,
        centerY + Math.sin(rad) * radius
      );

      const hsvColor = hslToRGB(angle, 100, 50);
      gradient.addColorStop(0, `rgba(${hsvColor[0]}, ${hsvColor[1]}, ${hsvColor[2]}, 0.2)`);
      gradient.addColorStop(1, `rgb(${hsvColor[0]}, ${hsvColor[1]}, ${hsvColor[2]})`);

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.moveTo(centerX + Math.cos(rad) * innerRadius, centerY + Math.sin(rad) * innerRadius);
      ctx.lineTo(centerX + Math.cos(rad) * radius, centerY + Math.sin(rad) * radius);
      ctx.lineTo(centerX + Math.cos(nextRad) * radius, centerY + Math.sin(nextRad) * radius);
      ctx.lineTo(centerX + Math.cos(nextRad) * innerRadius, centerY + Math.sin(nextRad) * innerRadius);
      ctx.fill();
    }

    // Draw outer ring border for definition
    ctx.strokeStyle = 'rgba(232, 234, 237, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Draw inner ring border
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.stroke();

    // Draw center circle with subtle background
    ctx.fillStyle = 'rgba(20, 25, 35, 0.6)';
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius * 0.95, 0, Math.PI * 2);
    ctx.fill();

    // Draw current hue indicator (larger for easier dragging)
    const currentRad = ((hue - 90) * Math.PI) / 180;
    const indicatorX = centerX + Math.cos(currentRad) * (radius + 5);
    const indicatorY = centerY + Math.sin(currentRad) * (radius + 5);

    // Outer glow ring
    ctx.strokeStyle = 'rgba(0, 255, 0, 0.4)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(indicatorX, indicatorY, 18, 0, Math.PI * 2);
    ctx.stroke();

    // Indicator dot (larger, 14px → easier to drag)
    const indicatorColor = hslToRGB(hue, 100, 50);
    ctx.fillStyle = `rgb(${indicatorColor[0]}, ${indicatorColor[1]}, ${indicatorColor[2]})`;
    ctx.beginPath();
    ctx.arc(indicatorX, indicatorY, 14, 0, Math.PI * 2);
    ctx.fill();

    // White border on indicator
    ctx.strokeStyle = 'rgba(255, 255, 255, 1)';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Draw hue value in center
    ctx.fillStyle = 'rgba(232, 234, 237, 0.9)';
    ctx.font = 'bold 24px Inter, system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${Math.round(hue)}°`, centerX, centerY);
  }, [hue, canvasSize]);

  // Calculate hue from mouse position
  const calculateHueFromEvent = useCallback((e: React.MouseEvent<HTMLCanvasElement> | MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    const x = (e as any).clientX - rect.left;
    const y = (e as any).clientY - rect.top;

    // Use canvasSize (CSS size) not canvas.width (scaled by DPR) for calculation
    const centerX = canvasSize.width / 2;
    const centerY = canvasSize.height / 2;

    const angle = Math.atan2(y - centerY, x - centerX);
    const hueValue = (angle * 180) / Math.PI + 90;
    return ((hueValue % 360) + 360) % 360;
  }, [canvasSize]);

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

  // Global drag tracking (works outside canvas bounds)
  useEffect(() => {
    if (!isDragging) return;

    const handleGlobalMouseMove = (e: MouseEvent) => {
      const newHue = calculateHueFromEvent(e as any);
      if (newHue !== null) {
        updateHueThrottled(newHue);
      }
    };

    const handleGlobalMouseUp = () => {
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

    document.addEventListener('mousemove', handleGlobalMouseMove);
    document.addEventListener('mouseup', handleGlobalMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove);
      document.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [isDragging, calculateHueFromEvent, updateHueThrottled, onChange]);

  const size = compact ? 140 : 280;

  return (
    <div ref={containerRef} className="w-full aspect-square max-h-96 flex flex-col items-center gap-2">
      <canvas
        ref={canvasRef}
        style={{
          width: `${canvasSize.width}px`,
          height: `${canvasSize.height}px`,
          cursor: disabled ? 'not-allowed' : 'crosshair'
        }}
        className={`rounded-lg transition-opacity ${disabled ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        onClick={handleCanvasClick}
        onMouseDown={handleMouseDown}
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
