/**
 * Fixture Controls
 *
 * Rendered from the zone's DERIVED capabilities rather than from a hardware
 * type, so one component serves every fixture shape:
 *
 *   switch_binary     -> power switch
 *   dimming           -> brightness slider
 *   color_control_rgb -> hue picker
 *   (no colour)       -> read-only swatch of the diode's declared colour
 *
 * A MOSFET-dimmed white diode therefore never shows a colour picker: it cannot
 * produce a colour, and the backend would reject the request with a 409 anyway.
 */

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Card } from "@/shared/ui/card";
import { PowerSwitch } from "@/shared/ui/power-switch";
import { Slider } from "@/shared/ui/slider";
import { Button } from "@/shared/ui/button";
import { HueColorPicker } from "@/shared/components/color/HueColorPicker";
import { rgbToHue } from "@/shared/utils/colorConversions";
import {
  setZoneBrightness,
  setZoneColor,
  setZoneIsOn,
  setZoneRenderMode,
} from "@/features/nodes/api/rig.commands";
import { FixturePreview } from "./FixturePreview";
import type { RemoteZone } from "@/shared/types/domain/node";

interface FixtureControlsProps {
  zone: RemoteZone;
}

function NominalColorSwatch({ color }: { color: [number, number, number] }): JSX.Element {
  return (
    <div className="flex items-center gap-2">
      <span
        className="w-5 h-5 rounded-full border border-gray-600 shrink-0"
        style={{ backgroundColor: `rgb(${color.join(",")})` }}
        aria-label="Declared physical colour"
      />
      <span className="text-xs text-gray-400">
        Fixed colour &mdash; set by the fitted diode, not controllable
      </span>
    </div>
  );
}

export function FixtureControls({ zone }: FixtureControlsProps): JSX.Element {
  const [brightness, setBrightness] = useState(zone.state.brightness);
  const [hue, setHue] = useState(() => rgbToHue(...zone.state.color.rgb));

  const canDim = zone.capabilities.includes("dimming");
  const canSetColor = zone.capabilities.includes("color_control_rgb");
  const isBreathing = zone.state.render_mode === "BREATHE";

  const primaryFixture = zone.fixtures[0];
  const pixelCount = Math.max(1, primaryFixture?.addressable_group_count ?? 1);

  const handleBrightnessCommit = (value: number[]) => {
    setBrightness(value[0]);
    setZoneBrightness(zone.zone_id, value[0]);
  };

  const handleHueChange = (newHue: number) => {
    setHue(newHue);
    setZoneColor(zone.zone_id, { mode: "HUE", hue: newHue });
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold truncate">{zone.display_name}</div>
          <div className="text-xs text-gray-400">
            {zone.fixtures.map((fixture) => fixture.label).join(", ") || "No fixtures"}
          </div>
        </div>
        <PowerSwitch
          checked={zone.state.is_on}
          onCheckedChange={(checked) => setZoneIsOn(zone.zone_id, checked)}
          label={`${zone.display_name} power`}
        />
      </div>

      {!zone.in_sync && (
        <div className="flex items-center gap-2 text-xs text-amber-400">
          <AlertTriangle className="w-3 h-3 shrink-0" />
          <span>Not confirmed by the device &mdash; retrying</span>
        </div>
      )}

      {primaryFixture && (
        <FixturePreview fixture={primaryFixture} state={zone.state} pixelCount={pixelCount} />
      )}

      {canDim && (
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
      )}

      {canSetColor ? (
        <HueColorPicker value={hue} onChange={handleHueChange} disabled={!zone.state.is_on} />
      ) : (
        primaryFixture?.config.nominal_color && (
          <NominalColorSwatch color={primaryFixture.config.nominal_color} />
        )
      )}

      <div className="flex items-center gap-2">
        <Button
          variant={isBreathing ? "default" : "outline"}
          size="sm"
          onClick={() => setZoneRenderMode(zone.zone_id, isBreathing ? "STATIC" : "BREATHE")}
        >
          {isBreathing ? "Stop breathing" : "Breathe"}
        </Button>
        <span className="text-xs text-gray-500">
          {zone.capabilities.join(", ")}
        </span>
      </div>
    </Card>
  );
}
