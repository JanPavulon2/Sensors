export interface Color {
  mode: 'HUE' | 'PRESET' | 'RGB'; 
  hue?: number;
  rgb?: [number, number, number];
  preset_name?: string;
}