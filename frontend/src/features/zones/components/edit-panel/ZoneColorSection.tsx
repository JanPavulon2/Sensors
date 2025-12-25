/**
 * Zone Color Section
 * Collapsible section for color and brightness control
 */

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Zone } from '@/shared/types/domain/zone';
import { Slider } from '@/shared/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { HueColorPicker, ColorPresetSelector } from '@/shared/components/color';
import { useUpdateZoneColorMutation, useUpdateZoneBrightnessMutation } from '@/features/zones/api';

interface ZoneColorSectionProps {
  zone: Zone;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
}

export function ZoneColorSection({
  zone,
  expanded = true,
  onToggle,
}: ZoneColorSectionProps) {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const colorMutation = useUpdateZoneColorMutation(zone.id);
  const brightnessMutation = useUpdateZoneBrightnessMutation(zone.id);

  const handleToggle = () => {
    const newState = !isExpanded;
    setIsExpanded(newState);
    onToggle?.(newState);
  };

  const handleBrightnessChange = (value: number[]) => {
    brightnessMutation.mutate({
      brightness: value[0],
    });
  };

  return (
    <div className="border-t border-border-default">
      {/* Section Header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-4 hover:bg-bg-elevated transition-colors"
      >
        <h3 className="text-base font-semibold text-text-primary">Appearance</h3>
        <ChevronDown
          className={`w-4 h-4 text-text-secondary transition-transform ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Section Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 bg-bg-app">
          {/* Brightness Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-text-primary">Brightness</label>
              <span className="text-sm font-mono text-accent-primary">
                {Math.round((zone.state.brightness / 255) * 100)}%
              </span>
            </div>
            <Slider
              value={[zone.state.brightness || 255]}
              onValueChange={handleBrightnessChange}
              max={255}
              step={1}
              disabled={brightnessMutation.isPending}
              className="w-full"
            />
          </div>

          {/* Color Picker Tabs */}
          <Tabs defaultValue="hue" className="w-full">
            <TabsList className="w-full grid grid-cols-2">
              <TabsTrigger value="hue">🎨 Hue</TabsTrigger>
              <TabsTrigger value="preset">⭐ Preset</TabsTrigger>
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
                      preset: presetName,
                    },
                  });
                }}
                disabled={colorMutation.isPending}
              />
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}
