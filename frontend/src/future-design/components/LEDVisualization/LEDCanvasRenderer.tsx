/**
 * LED Canvas Renderer - Realistic LED Strip Visualization
 *
 * Features:
 * - Canvas-based pixel rendering (high performance)
 * - Multi-layer glow effects (bloom, color bleeding)
 * - Real-time WebSocket frame updates (60 FPS target)
 * - Zone boundary visualization
 * - Zoom & pan controls
 * - Touch/mouse interaction
 *
 * Performance: Targets 60 FPS on desktop, 30 FPS on mobile
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import type { ZoneCombined, LEDCanvasProps } from '../../types/index';
import { getGlowParameters, getDefaultPresets } from '../../utils/colors';
import styles from './LEDCanvasRenderer.module.css';

interface CanvasState {
  zoom: number;
  panX: number;
  panY: number;
}

/**
 * LEDCanvasRenderer Component
 * Main canvas for rendering addressable LED pixels with realistic effects
 */
export const LEDCanvasRenderer: React.FC<LEDCanvasProps> = ({
  zones,
  selectedZoneId,
  orientation = 'horizontal',
  pixelSize = 24,
  gapBetweenZones = 12,
  zoom = 1,
  onZoneSelect,
  // onPixelHover is unused in current implementation
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeRef = useRef<number>(0);

  // Convert zones to array if it's a Map
  const zonesArray: ZoneCombined[] = zones instanceof Map ? Array.from(zones.values()) : (zones as ZoneCombined[]);
  const zonesCount: number = zones instanceof Map ? zones.size : (zones as ZoneCombined[]).length;

  const [canvasState, setCanvasState] = useState<CanvasState>({
    zoom,
    panX: 0,
    panY: 0,
  });

  const [hoveredPixel] = useState<{ zone: string; pixel: number } | null>(null);
  const [canvasDimensions, setCanvasDimensions] = useState({ width: 0, height: 0 });

  // ============ Calculate Layout ============

  /**
   * Calculate canvas dimensions based on zones and orientation
   * Maintains perfect aspect ratio to prevent pixel stretching
   */
  const calculateDimensions = useCallback(() => {
    if (!containerRef.current) return;

    const container = containerRef.current.getBoundingClientRect();
    const sortedZones = zonesArray.sort((a: ZoneCombined, b: ZoneCombined) => a.order - b.order);

    // Calculate ideal content dimensions
    let contentWidth = 0;
    let contentHeight = 0;

    if (orientation === 'horizontal') {
      // Horizontal strip: zones arranged left to right
      contentWidth = sortedZones.reduce((sum: number, zone: ZoneCombined, i: number) => {
        return sum + zone.pixelCount * pixelSize + (i < sortedZones.length - 1 ? gapBetweenZones : 0);
      }, 0);
      contentHeight = pixelSize;
    } else {
      // Vertical strip: zones arranged top to bottom
      contentHeight = sortedZones.reduce((sum: number, zone: ZoneCombined, i: number) => {
        return sum + zone.pixelCount * pixelSize + (i < sortedZones.length - 1 ? gapBetweenZones : 0);
      }, 0);
      contentWidth = pixelSize;
    }

    // Add padding and label space
    const padding = 40;
    const labelSpace = 30;
    const idealWidth = contentWidth + padding * 2;
    const idealHeight = contentHeight + padding * 2 + labelSpace;

    // Scale to fit container while maintaining aspect ratio
    let finalWidth = Math.min(idealWidth, container.width);
    let finalHeight = (finalWidth / idealWidth) * idealHeight;

    if (finalHeight > container.height) {
      finalHeight = container.height;
      finalWidth = (finalHeight / idealHeight) * idealWidth;
    }

    setCanvasDimensions({
      width: Math.max(300, finalWidth),
      height: Math.max(150, finalHeight),
    });
  }, [zones, orientation, pixelSize, gapBetweenZones]);

  // ============ Render Loop ============

  /**
   * Main rendering function
   * Uses canvas 2D context for pixel drawing with multi-layer glow
   */
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { zoom: z, panX, panY } = canvasState;

    // Clear canvas
    ctx.fillStyle = 'rgba(10, 14, 20, 0.95)'; // Subtle dark background
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Apply zoom and pan transforms
    ctx.save();
    ctx.translate(canvas.width / 2 + panX, canvas.height / 2 + panY);
    ctx.scale(z, z);
    ctx.translate(-canvas.width / (2 * z), -canvas.height / (2 * z));

    // Sort zones by order
    const sortedZones = zonesArray.sort((a: ZoneCombined, b: ZoneCombined) => a.order - b.order);

    let currentX = 30;
    let currentY = 30;

    // Render each zone
    sortedZones.forEach((zone) => {
      renderZone(ctx, zone, currentX, currentY, selectedZoneId === zone.id);

      if (orientation === 'horizontal') {
        currentX += zone.pixelCount * pixelSize + gapBetweenZones;
      } else {
        currentY += zone.pixelCount * pixelSize + gapBetweenZones;
      }
    });

    ctx.restore();
  }, [zones, orientation, pixelSize, gapBetweenZones, selectedZoneId, canvasState]);

  /**
   * Render a single zone
   */
  const renderZone = (
    ctx: CanvasRenderingContext2D,
    zone: ZoneCombined,
    startX: number,
    startY: number,
    isSelected: boolean
  ) => {
    // Zone label - improved readability
    ctx.fillStyle = 'rgba(0, 255, 0, 0.9)';
    ctx.font = 'bold 14px monospace';
    ctx.textBaseline = 'bottom';
    ctx.fillText(zone.displayName, startX, startY - 8);

    // Render pixels
    for (let i = 0; i < zone.pixelCount; i++) {
      let pixelX: number;
      let pixelY: number;

      if (orientation === 'horizontal') {
        pixelX = startX + i * pixelSize;
        pixelY = startY;
      } else {
        pixelX = startX;
        pixelY = startY + i * pixelSize;
      }

      renderPixel(ctx, pixelX, pixelY, zone);
    }

    // Zone border (if selected)
    if (isSelected) {
      ctx.strokeStyle = 'rgba(0, 245, 255, 0.6)';
      ctx.lineWidth = 2;
      const width = orientation === 'horizontal' ? zone.pixelCount * pixelSize : pixelSize;
      const height = orientation === 'horizontal' ? pixelSize : zone.pixelCount * pixelSize;
      ctx.strokeRect(startX - 2, startY - 2, width + 4, height + 4);
    }
  };

  /**
   * Render a single LED pixel with glow effect and animation
   */
  const renderPixel = (ctx: CanvasRenderingContext2D, x: number, y: number, zone: ZoneCombined) => {
    // Get pixel color based on mode
    let rgb: [number, number, number];

    if (zone.color.mode === 'HUE' && zone.color.hue !== undefined) {
      rgb = hueToRGB(zone.color.hue);
    } else if (zone.color.mode === 'RGB' && zone.color.rgb) {
      rgb = zone.color.rgb;
    } else if (zone.color.mode === 'PRESET' && zone.color.preset) {
      // Look up preset color
      const presets = getDefaultPresets();
      const preset = presets.find((p) => p.name === zone.color.preset);
      rgb = preset?.rgb || [255, 255, 255];
    } else {
      rgb = [255, 255, 255];
    }

    // Apply animation effects
    let brightness = Math.max(0, Math.min(255, zone.brightness || 100));

    // Apply animation-specific brightness modulation
    if (zone.mode === 'BREATHE') {
      // Pulsing brightness effect
      const pulse = Math.sin(timeRef.current / 300) * 0.5 + 0.5; // 0 to 1
      brightness = brightness * (0.3 + pulse * 0.7); // Breathe from 30% to 100%
    } else if (zone.mode === 'COLOR_CYCLE') {
      // Pulsing glow effect
      const pulse = Math.sin(timeRef.current / 500) * 0.3 + 0.7;
      brightness = brightness * pulse;
    }

    const brightnessFactor = brightness / 255;
    const adjustedRGB: [number, number, number] = [
      Math.round(rgb[0] * brightnessFactor),
      Math.round(rgb[1] * brightnessFactor),
      Math.round(rgb[2] * brightnessFactor),
    ];

    // Calculate glow parameters based on brightness
    const glow = getGlowParameters(brightness, 1.0);

    const radius = pixelSize / 2;
    const centerX = x + radius;
    const centerY = y + radius;

    // Draw multiple glow layers (outer to inner)
    const colors = [
      `rgba(${adjustedRGB[0]}, ${adjustedRGB[1]}, ${adjustedRGB[2]}, ${glow.opacity2})`,
      `rgba(${adjustedRGB[0]}, ${adjustedRGB[1]}, ${adjustedRGB[2]}, ${glow.opacity1})`,
      `rgba(${adjustedRGB[0]}, ${adjustedRGB[1]}, ${adjustedRGB[2]}, ${glow.opacity0})`,
    ];

    const radii = [glow.radius2, glow.radius1, glow.radius0];

    // Draw glow layers
    colors.forEach((color, i) => {
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radii[i]);
      gradient.addColorStop(0, color);
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(centerX - radii[i], centerY - radii[i], radii[i] * 2, radii[i] * 2);
    });

    // Draw core pixel - perfect circle
    ctx.fillStyle = `rgb(${adjustedRGB[0]}, ${adjustedRGB[1]}, ${adjustedRGB[2]})`;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.65, 0, Math.PI * 2);
    ctx.fill();

    // Bright highlight for shininess
    const hlGradient = ctx.createRadialGradient(
      centerX - radius * 0.25,
      centerY - radius * 0.25,
      0,
      centerX,
      centerY,
      radius * 0.7
    );
    hlGradient.addColorStop(0, `rgba(255, 255, 255, ${0.4 * brightnessFactor})`);
    hlGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = hlGradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius * 0.65, 0, Math.PI * 2);
    ctx.fill();
  };

  /**
   * Convert hue (0-360) to RGB
   * Inline for performance
   */
  const hueToRGB = (hue: number): [number, number, number] => {
    const h = ((hue % 360) + 360) % 360;
    const c = 255;
    const hh = h / 60;
    const i = Math.floor(hh);
    const ff = hh - i;
    const x = c * (1 - ff);
    const y = c * ff;

    switch (i) {
      case 0:
        return [c, y, 0];
      case 1:
        return [x, c, 0];
      case 2:
        return [0, c, y];
      case 3:
        return [0, x, c];
      case 4:
        return [y, 0, c];
      default:
        return [c, 0, x];
    }
  };

  // ============ Event Handlers ============

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Find zone at position
    const sortedZones = zonesArray.sort((a: ZoneCombined, b: ZoneCombined) => a.order - b.order);
    let currentX = 30;
    let currentY = 30;

    for (const zone of sortedZones) {
      const zoneX = currentX;
      const zoneY = currentY;
      const zoneWidth = orientation === 'horizontal' ? zone.pixelCount * pixelSize : pixelSize;
      const zoneHeight = orientation === 'horizontal' ? pixelSize : zone.pixelCount * pixelSize;

      if (x >= zoneX && x <= zoneX + zoneWidth && y >= zoneY && y <= zoneY + zoneHeight) {
        onZoneSelect?.(zone.id);
        return;
      }

      if (orientation === 'horizontal') {
        currentX += zone.pixelCount * pixelSize + gapBetweenZones;
      } else {
        currentY += zone.pixelCount * pixelSize + gapBetweenZones;
      }
    }
  };

  const handleCanvasWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setCanvasState((prev) => ({
      ...prev,
      zoom: Math.max(0.5, Math.min(3, prev.zoom * delta)),
    }));
  };

  const handleResetView = () => {
    setCanvasState({ zoom: 1, panX: 0, panY: 0 });
  };

  // ============ Effects ============

  useEffect(() => {
    calculateDimensions();
    window.addEventListener('resize', calculateDimensions);
    return () => window.removeEventListener('resize', calculateDimensions);
  }, [calculateDimensions]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Set canvas internal resolution (actual pixel size)
    // This must match the CSS size to avoid stretching
    canvas.width = Math.floor(canvasDimensions.width);
    canvas.height = Math.floor(canvasDimensions.height);

    // Ensure CSS size matches to prevent canvas scaling
    canvas.style.width = `${canvasDimensions.width}px`;
    canvas.style.height = `${canvasDimensions.height}px`;

    render();
  }, [canvasDimensions, render]);

  useEffect(() => {
    let animationId: number;
    let lastTime = Date.now();

    const animate = () => {
      // Update time for animation effects
      const now = Date.now();
      timeRef.current += now - lastTime;
      lastTime = now;

      render();
      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, [render]);

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.toolbar}>
        <button onClick={handleResetView} className={styles.button} title="Reset zoom and pan">
          🔄 Reset View
        </button>
        <span className={styles.zoomLevel}>{(canvasState.zoom * 100).toFixed(0)}%</span>
      </div>

      <canvas
        ref={canvasRef}
        className={styles.canvas}
        onClick={handleCanvasClick}
        onWheel={handleCanvasWheel}
        style={{
          cursor: 'pointer',
          transition: 'all 0.1s ease-out',
        }}
      />

      {hoveredPixel && (
        <div className={styles.tooltip}>
          {hoveredPixel.zone} - Pixel {hoveredPixel.pixel}
        </div>
      )}

      <div className={styles.info}>
        <p>
          {zonesCount} zones • {zonesArray.reduce((sum: number, z: ZoneCombined) => sum + z.pixelCount, 0)} pixels
        </p>
        <p className={styles.hint}>🖱️ Click zone • 🔄 Scroll to zoom • Drag to pan</p>
      </div>
    </div>
  );
};

export default LEDCanvasRenderer;
