/**
 * Zone Color Section
 * Color and brightness control (always expanded)
 */

import { useCallback } from 'react';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';
import { Slider } from '@/shared/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { HueColorPicker, ColorPresetSelector } from '@/shared/components/color';
import { api } from '@/shared/api/client';

interface ZoneColorSectionProps {
  zone: ZoneSnapshot;
}

export function ZoneColorSection({
  zone,
}: ZoneColorSectionProps) {
  const handleBrightnessChange = useCallback((value: number[]) => {
    // Send brightness change directly to backend (like power toggle)
    api.put(`/v1/zones/${zone.id}/brightness`, {
      brightness: value[0],
    }).catch((error) => {
      console.error('Failed to update brightness:', error);
    });
  }, [zone.id]);

  const handleHueChange = useCallback((hue: number) => {
    // Send hue change directly to backend
    api.put(`/v1/zones/${zone.id}/color`, {
      color: {
        mode: 'HUE',
        hue: Math.round(hue),
      },
    }).catch((error) => {
      console.error('Failed to update color:', error);
    });
  }, [zone.id]);

  const handlePresetSelect = useCallback((presetName: string) => {
    // Send preset change directly to backend
    api.put(`/v1/zones/${zone.id}/color`, {
      color: {
        mode: 'PRESET',
        preset_name: presetName,
      },
    }).catch((error) => {
      console.error('Failed to update color:', error);
    });
  }, [zone.id]);

  // Determine default tab based on color mode
  const defaultColorTab = zone.color.mode === 'PRESET' ? 'preset' : 'hue';

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
                {zone.brightness}%
              </span>
            </div>
            <Slider
              value={[zone.brightness]}
              onValueChange={handleBrightnessChange}
              min={0}
              max={100}
              step={1}
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
                value={zone.color.hue || 0}
                onChange={handleHueChange}
              />
            </TabsContent>

            <TabsContent value="preset" className="mt-3">
              <ColorPresetSelector
                currentPreset={zone.color.preset_name}
                onSelect={handlePresetSelect}
              />
            </TabsContent>
          </Tabs>
      </div>
    </div>
  );
}
