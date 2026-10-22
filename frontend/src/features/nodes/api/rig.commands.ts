import { api } from '@/shared/api/client';
import type {
  ChannelRole,
  RemoteZoneRenderMode,
  WhiteProfile,
} from '@/shared/types/domain/node';

export function setZoneColor(
  zoneId: string,
  color: { mode: 'RGB'; rgb: [number, number, number] } | { mode: 'HUE'; hue: number }
): Promise<void> {
  return api.put(`/v1/rig/zones/${zoneId}/color`, { color });
}

export function setZoneBrightness(zoneId: string, brightness: number): Promise<void> {
  return api.put(`/v1/rig/zones/${zoneId}/brightness`, { brightness });
}

export function setZoneIsOn(zoneId: string, isOn: boolean): Promise<void> {
  return api.put(`/v1/rig/zones/${zoneId}/is-on`, { is_on: isOn });
}

export function setZoneRenderMode(zoneId: string, renderMode: RemoteZoneRenderMode): Promise<void> {
  return api.put(`/v1/rig/zones/${zoneId}/render-mode`, { render_mode: renderMode });
}

export interface UpsertFixtureInstancePayload {
  id: string;
  definition_id: string;
  node_id: string;
  label: string;
  nominal_color?: [number, number, number] | null;
  white_profile?: WhiteProfile | null;
  bindings: Array<{ module_instance_id: string; channel_name: string; role: ChannelRole }>;
}

export function upsertFixtureInstance(payload: UpsertFixtureInstancePayload): Promise<void> {
  return api.put(`/v1/rig/fixtures/${payload.id}`, payload);
}

export function deleteFixtureInstance(instanceId: string): Promise<void> {
  return api.delete(`/v1/rig/fixtures/${instanceId}`);
}
