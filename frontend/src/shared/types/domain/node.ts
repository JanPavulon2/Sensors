/**
 * Remote node (ESP32) types for the Nodes page and realtime store.
 * Field names/casing mirror the backend DTOs exactly (see
 * src/api/dto/node_snapshot_dto.py, src/api/routes/nodes.py).
 */

export type NodeType = "ESP32" | "RASPBERRY_PI_4" | "RASPBERRY_PI_5" | "FRONTEND_RUNTIME" | "OTHER";

export interface NodeSnapshot {
  instance_id: string;
  external_node_id: string;
  node_type: NodeType | string;
  address: string;
  command_port: number;
  firmware: string;
  capabilities: string[];
  online: boolean;
  last_seen: string;
  declared_device_capabilities?: string[];
}

export interface RemoteZoneColor {
  rgb: [number, number, number];
}

export type RemoteZoneRenderMode = "STATIC" | "BREATHE";

export interface RemoteZoneState {
  is_on: boolean;
  brightness: number;
  color: RemoteZoneColor;
  render_mode: RemoteZoneRenderMode;
}

export interface RemoteZone {
  node_id: string;
  zone_label: string;
  display_name: string;
  pixel_count: number;
  sync_group: string | null;
  state: RemoteZoneState;
}
