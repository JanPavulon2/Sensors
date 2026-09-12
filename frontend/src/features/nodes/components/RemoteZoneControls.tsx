import { useState } from "react";
import { Card } from "@/shared/ui/card";
import { PowerSwitch } from "@/shared/ui/power-switch";
import { Slider } from "@/shared/ui/slider";
import { HueColorPicker } from "@/shared/components/color/HueColorPicker";
import { rgbToHue } from "@/shared/utils/colorConversions";
import {
  setRemoteZoneBrightness,
  setRemoteZoneColor,
  setRemoteZoneIsOn,
} from "@/features/nodes/api/node.commands";
import type { RemoteZone } from "@/shared/types/domain/node";

interface RemoteZoneControlsProps {
  zone: RemoteZone;
}

export function RemoteZoneControls({ zone }: RemoteZoneControlsProps): JSX.Element {
  const [brightness, setBrightness] = useState(zone.state.brightness);
  const [hue, setHue] = useState(() => rgbToHue(...zone.state.color.rgb));

  const handlePowerChange = (checked: boolean) => {
    setRemoteZoneIsOn(zone.node_id, zone.zone_label, checked);
  };

  const handleBrightnessCommit = (value: number[]) => {
    const newBrightness = value[0];
    setBrightness(newBrightness);
    setRemoteZoneBrightness(zone.node_id, zone.zone_label, newBrightness);
  };

  const handleHueChange = (newHue: number) => {
    setHue(newHue);
    setRemoteZoneColor(zone.node_id, zone.zone_label, { mode: "HUE", hue: newHue });
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">{zone.display_name}</div>
          <div className="text-xs text-gray-400">{zone.pixel_count} pixels</div>
        </div>
        <PowerSwitch
          checked={zone.state.is_on}
          onCheckedChange={handlePowerChange}
          label={`${zone.display_name} power`}
        />
      </div>

      <div>
        <label className="text-xs text-gray-400 block mb-1">Brightness</label>
        <Slider
          value={[brightness]}
          min={0}
          max={100}
          step={1}
          onValueChange={(value) => setBrightness(value[0])}
          onValueCommit={handleBrightnessCommit}
        />
      </div>

      <HueColorPicker value={hue} onChange={handleHueChange} disabled={!zone.state.is_on} />
    </Card>
  );
}
