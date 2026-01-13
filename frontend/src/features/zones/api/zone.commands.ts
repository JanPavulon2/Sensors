import { api } from '@/shared/api/client';

export function setZoneBrightness(
  zoneId: string,
  brightness: number
): Promise<void> {
  return api.put(`/v1/zones/${zoneId}/brightness`, { brightness });
}

export function setZonePower(
  zoneId: string,
  is_on: boolean
): Promise<void> {
  return api.put(`/v1/zones/${zoneId}/is-on`, { is_on });
}

export function setZoneColor(
  zoneId: string,
  color: any
): Promise<void> {
  return api.put(`/v1/zones/${zoneId}/color`, { color });
}

export function setZoneRenderMode(
  zoneId: string,
  render_mode: 'STATIC' | 'ANIMATION'
): Promise<void> {
  return api.put(`/v1/zones/${zoneId}/render-mode`, { render_mode });
}

export function setZoneAnimationParameters(
  zoneId: string,
  parameters: Record<string, any>
): Promise<void> {
  return api.put(`/v1/zones/${zoneId}/animation/parameters`, {
    parameters,
  });
}