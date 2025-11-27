/**
 * Zone Card Component
 * Displays zone information and controls (color, brightness)
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { useUpdateZoneColorMutation, useUpdateZoneBrightnessMutation } from '@/hooks/useZones';
import type { Zone } from '@/types/zone';
import { HexColorPicker } from 'react-colorful';
import { useState } from 'react';

interface ZoneCardProps {
  zone: Zone;
  onSelect?: (zoneId: string) => void;
}

export function ZoneCard({ zone, onSelect }: ZoneCardProps): JSX.Element {
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [tempColor, setTempColor] = useState(
    zone.state.color.rgb
      ? `#${zone.state.color.rgb.map((c) => c.toString(16).padStart(2, '0')).join('')}`
      : '#00E5FF'
  );

  const colorMutation = useUpdateZoneColorMutation(zone.id);
  const brightnessMutation = useUpdateZoneBrightnessMutation(zone.id);

  const handleColorChange = (color: string) => {
    setTempColor(color);
    // Convert hex to RGB
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);

    colorMutation.mutate({
      color: {
        mode: 'RGB',
        rgb: [r, g, b],
      },
    });
  };

  const handleBrightnessChange = (value: number[]) => {
    brightnessMutation.mutate({
      brightness: value[0],
    });
  };

  const colorRgb = zone.state.color.rgb
    ? `rgb(${zone.state.color.rgb.join(',')})`
    : '#00E5FF';

  return (
    <Card className="hover:border-accent-primary transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-lg">{zone.name}</CardTitle>
            <p className="text-xs text-text-tertiary mt-1">
              {zone.pixel_count} pixels
            </p>
          </div>
          <div
            className="w-10 h-10 rounded border-2 border-border"
            style={{ backgroundColor: colorRgb }}
            title="Zone color"
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Color Preview & Picker */}
        <div className="space-y-2">
          <Label>Color</Label>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowColorPicker(!showColorPicker)}
              className="w-8 h-8 rounded border-2 border-border-default hover:border-accent-primary transition-colors"
              style={{ backgroundColor: colorRgb }}
            />
            <span className="text-sm font-mono text-text-secondary">{tempColor}</span>
          </div>
          {showColorPicker && (
            <div className="pt-2">
              <HexColorPicker color={tempColor} onChange={handleColorChange} />
            </div>
          )}
        </div>

        {/* Brightness Control */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Brightness</Label>
            <span className="text-sm font-medium text-accent-primary">
              {Math.round((zone.state.brightness / 255) * 100)}%
            </span>
          </div>
          <Slider
            value={[zone.state.brightness]}
            onValueChange={handleBrightnessChange}
            max={255}
            step={1}
            disabled={brightnessMutation.isPending}
            className="w-full"
          />
        </div>

        {/* Status */}
        <div className="pt-2 border-t border-border-subtle">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <div
              className={`w-2 h-2 rounded-full ${zone.state.enabled ? 'bg-success' : 'bg-warning'}`}
            />
            {zone.state.enabled ? 'Enabled' : 'Disabled'}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1"
            onClick={() => onSelect?.(zone.id)}
          >
            Control
          </Button>
          <Button size="sm" variant="ghost" className="flex-1">
            Details
          </Button>
        </div>

        {/* Loading States */}
        {(colorMutation.isPending || brightnessMutation.isPending) && (
          <div className="text-xs text-text-tertiary italic">
            Updating...
          </div>
        )}
        {colorMutation.isError && (
          <div className="text-xs text-error">Color update failed</div>
        )}
        {brightnessMutation.isError && (
          <div className="text-xs text-error">Brightness update failed</div>
        )}
      </CardContent>
    </Card>
  );
}

export default ZoneCard;
