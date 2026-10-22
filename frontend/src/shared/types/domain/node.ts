/**
 * Remote node (ESP32) and rig types.
 * Field names/casing mirror the backend DTOs exactly (see
 * src/api/dto/node_snapshot_dto.py, src/api/dto/rig_dto.py).
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
  /**
   * Outcome of the last command delivery attempt. null means nothing has been
   * sent yet. Command delivery is fire-and-forget on the backend, so this is
   * the only signal that a command actually reached the node.
   */
  last_command_delivered?: boolean | null;
  /** Derived from what is actually wired to this node, not from its type. */
  device_capabilities?: string[];
  zone_ids?: string[];
}

/**
 * What a fixture or zone can physically do. Derived by the backend from
 * (driver control interface x component type x channel bindings) - the UI is
 * generated from this rather than from hardware types, so a plain white diode
 * simply never offers a colour picker.
 */
export type DeviceCapability =
  | "switch_binary"
  | "dimming"
  | "color_control_rgb"
  | "color_control_rgbw"
  | "addressable_pixels";

export type HardwareControlInterface = "ANALOG_PWM" | "ADDRESSABLE_DATA" | "CONSTANT_CURRENT_DRIVER";

export type LightComponentType = "SINGLE_COLOR" | "RGB" | "RGBW" | "ADDRESSABLE_PIXEL";

export type WhiteProfile = "COLD" | "WARM" | "NEUTRAL" | "TUNABLE";

export type ChannelRole = "SINGLE" | "RED" | "GREEN" | "BLUE" | "WHITE" | "DATA";

export interface DriverDefinition {
  id: string;
  name: string;
  control_interface: HardwareControlInterface;
  channels: string[];
  channel_count: number;
}

export interface FixtureDefinition {
  id: string;
  name: string;
  component_type: LightComponentType;
  /** Physical LEDs that emit. A COB strip has hundreds. */
  component_count: number;
  /** Independently drivable groups. A COB strip has one, a WS2812 strip has many. */
  addressable_group_count: number;
  is_individually_addressable: boolean;
  white_profile: WhiteProfile | null;
}

export interface RigCatalog {
  drivers: DriverDefinition[];
  fixtures: FixtureDefinition[];
}

export interface ChannelBinding {
  module_instance_id: string;
  channel_name: string;
  role: ChannelRole;
}

export interface FixtureInstanceConfig {
  /**
   * The physical colour of the fitted diode/strip. User-declared: no software
   * can discover what was actually wired in.
   */
  nominal_color?: [number, number, number];
  white_profile?: WhiteProfile;
  bindings?: ChannelBinding[];
}

export interface FixtureInstance {
  id: string;
  definition_id: string;
  node_id: string;
  label: string;
  config: FixtureInstanceConfig;
  capabilities: DeviceCapability[];
  component_type: LightComponentType | null;
  /** Physical LEDs that emit. A COB strip has hundreds. */
  component_count: number;
  /** Independently drivable groups - how many pixels to preview. */
  addressable_group_count: number;
}

export interface DriverInstance {
  id: string;
  definition_id: string;
  node_id: string;
  label: string;
  config: { channel_pins?: Record<string, number> };
}

export type RemoteZoneRenderMode = "STATIC" | "BREATHE";

export interface RemoteZoneState {
  is_on: boolean;
  brightness: number;
  color: { rgb: [number, number, number] };
  render_mode: RemoteZoneRenderMode;
}

export interface RemoteZone {
  zone_id: string;
  display_name: string;
  node_id: string;
  device_instance_ids: string[];
  sync_group: string | null;
  /** Intersection of its fixtures' capabilities - a zone can only offer what all of them support. */
  capabilities: DeviceCapability[];
  /** False when the node reported a state that differs from what the host intends. */
  in_sync: boolean;
  state: RemoteZoneState;
  fixtures: FixtureInstance[];
}
