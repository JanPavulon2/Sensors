/**
 * Shape-specific LED rendering utilities
 * Helpers for calculating LED positions and rendering different zone shapes
 */

import type { RGBColor } from '../ZonesDashboard/ZoneDetailCard';
import type { StripOrientation } from '../../types/index';

// ============ Strip (Linear) Layout ============

export interface StripLEDPosition {
  index: number;
  x: number;
  y: number;
}

export function calculateStripPositions(
  pixelCount: number,
  containerWidth: number,
  containerHeight: number,
  orientation: StripOrientation,
  padding: number = 8
): StripLEDPosition[] {
  const positions: StripLEDPosition[] = [];

  if (orientation === 'horizontal') {
    const availableWidth = containerWidth - padding * 2;
    const ledWidth = availableWidth / pixelCount;

    for (let i = 0; i < pixelCount; i++) {
      positions.push({
        index: i,
        x: padding + i * ledWidth + ledWidth / 2,
        y: containerHeight / 2,
      });
    }
  } else {
    // vertical
    const availableHeight = containerHeight - padding * 2;
    const ledHeight = availableHeight / pixelCount;

    for (let i = 0; i < pixelCount; i++) {
      positions.push({
        index: i,
        x: containerWidth / 2,
        y: padding + i * ledHeight + ledHeight / 2,
      });
    }
  }

  return positions;
}

// ============ Circle Layout ============

export interface CircleLEDPosition {
  index: number;
  x: number;
  y: number;
  angle: number;
}

export function calculateCirclePositions(
  pixelCount: number,
  containerWidth: number,
  containerHeight: number,
  padding: number = 8
): CircleLEDPosition[] {
  const positions: CircleLEDPosition[] = [];
  const centerX = containerWidth / 2;
  const centerY = containerHeight / 2;
  const maxRadius = Math.min(centerX, centerY) - padding;

  for (let i = 0; i < pixelCount; i++) {
    const angle = (i / pixelCount) * Math.PI * 2;
    const x = centerX + Math.cos(angle) * maxRadius;
    const y = centerY + Math.sin(angle) * maxRadius;

    positions.push({
      index: i,
      x,
      y,
      angle,
    });
  }

  return positions;
}

// ============ Matrix Layout ============

export interface MatrixLEDPosition {
  index: number;
  row: number;
  col: number;
  x: number;
  y: number;
}

export function calculateMatrixPositions(
  rows: number,
  columns: number,
  containerWidth: number,
  containerHeight: number,
  padding: number = 8
): MatrixLEDPosition[] {
  const positions: MatrixLEDPosition[] = [];
  const availableWidth = containerWidth - padding * 2;
  const availableHeight = containerHeight - padding * 2;

  const cellWidth = availableWidth / columns;
  const cellHeight = availableHeight / rows;

  let index = 0;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < columns; col++) {
      const x = padding + col * cellWidth + cellWidth / 2;
      const y = padding + row * cellHeight + cellHeight / 2;

      positions.push({
        index,
        row,
        col,
        x,
        y,
      });

      index++;
    }
  }

  return positions;
}

// ============ LED Rendering Helpers ============

export function renderLEDCircle(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  color: RGBColor
): void {
  // Glow halo
  const glow = ctx.createRadialGradient(x, y, radius * 0.9, x, y, radius * 1.6);
  glow.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.3)`);
  glow.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0)`);
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(x, y, radius * 1.6, 0, Math.PI * 2);
  ctx.fill();

  // Solid core
  ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}

export function renderLEDSquare(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  color: RGBColor
): void {
  const halfSize = size / 2;

  // Glow effect with outer shadow
  ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.2)`;
  ctx.fillRect(x - halfSize - 2, y - halfSize - 2, size + 4, size + 4);

  // Main rectangle
  ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
  ctx.fillRect(x - halfSize, y - halfSize, size, size);
}
