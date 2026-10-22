import { api } from '@/shared/api/client';

export function sendNodeCommand(
  nodeId: string,
  name: string,
  payload: Record<string, unknown> = {}
): Promise<void> {
  return api.post(`/v1/nodes/${nodeId}/command`, { name, payload });
}

export function setRemoteZoneColor(
  nodeId: string,
  zoneLabel: string,
  color: { mode: 'RGB'; rgb: [number, number, number] } | { mode: 'HUE'; hue: number }
): Promise<void> {
  return api.put(`/v1/nodes/${nodeId}/zones/${zoneLabel}/color`, { color });
}

export function setRemoteZoneBrightness(
  nodeId: string,
  zoneLabel: string,
  brightness: number
): Promise<void> {
  return api.put(`/v1/nodes/${nodeId}/zones/${zoneLabel}/brightness`, { brightness });
}

export function setRemoteZoneIsOn(
  nodeId: string,
  zoneLabel: string,
  isOn: boolean
): Promise<void> {
  return api.put(`/v1/nodes/${nodeId}/zones/${zoneLabel}/is-on`, { is_on: isOn });
}
