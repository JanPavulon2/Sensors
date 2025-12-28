/**
 * Zone Color Section
 * Color and brightness control (always expanded)
 */

import type { Zone } from '@/shared/types/domain/zone';
import { Slider } from '@/shared/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { HueColorPicker, ColorPresetSelector } from '@/shared/components/color';
import { useUpdateZoneColorMutation, useUpdateZoneBrightnessMutation } from '@/features/zones/api';

interface ZoneColorSectionProps {
  zone: Zone;
}

export function ZoneColorSection({
  zone,
}: ZoneColorSectionProps) {
  const colorMutation = useUpdateZoneColorMutation(zone.id);
  const brightnessMutation = useUpdateZoneBrightnessMutation(zone.id);

  const handleBrightnessChange = (value: number[]) => {
    brightnessMutation.mutate({
      brightness: value[0],
    });
  };

  // Determine default tab based on color mode
  const defaultColorTab = zone.state.color.mode === 'PRESET' ? 'preset' : 'hue';

  return (
    <div>
      {/* Section Header */}
      <h3 className="text-base font-semibold text-text-primary px-4 pt-4">Appearance</h3>

      {/* Section Content */}
      <div className="px-4 pb-4 space-y-6 bg-bg-app">
          {/* Brightness Slider */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-text-primary">Brightness</label>
              <span className="text-sm font-mono text-accent-primary">
                {zone.state.brightness}%
              </span>
            </div>
            <Slider
              value={[zone.state.brightness || 100]}
              onValueChange={handleBrightnessChange}
              min={0}
              max={100}
              step={1}
              disabled={brightnessMutation.isPending}
              className="w-full"
            />
          </div>

          {/* Color Picker Tabs */}
          <Tabs defaultValue={defaultColorTab} className="w-full">
            <TabsList variant="underline" className="w-full">
              <TabsTrigger variant="underline" value="hue">🎨 Hue</TabsTrigger>
              <TabsTrigger variant="underline" value="preset">⭐ Preset</TabsTrigger>
            </TabsList>

            <TabsContent value="hue" className="space-y-3 mt-3">
              <HueColorPicker
                value={zone.state.color.hue || 0}
                onChange={(hue) => {
                  colorMutation.mutate({
                    color: {
                      mode: 'HUE',
                      hue: Math.round(hue),
                    },
                  });
                }}
                disabled={colorMutation.isPending}
              />
            </TabsContent>

            <TabsContent value="preset" className="mt-3">
              <ColorPresetSelector
                currentPreset={zone.state.color.preset_name}
                onSelect={(presetName) => {
                  colorMutation.mutate({
                    color: {
                      mode: 'PRESET',
                      preset_name: presetName,
                    },
                  });
                }}
                disabled={colorMutation.isPending}
              />
            </TabsContent>
          </Tabs>
      </div>
    </div>
  );
}
