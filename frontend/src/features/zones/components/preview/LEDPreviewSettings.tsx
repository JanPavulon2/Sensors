/**
 * LED Preview Settings Component
 * Controls for customizing LED preview appearance
 */

import { Sliders } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Slider } from '@/shared/ui/slider';
import { usePreviewSettingsStore, type LEDShape } from '../../stores/previewSettingsStore';

export function LEDPreviewSettings() {
  const { settings, setShape, setSize, setSpacing, setGlowIntensity, setShowGlow, resetToDefaults } =
    usePreviewSettingsStore();

  const shapes: Array<{ value: LEDShape; label: string; icon: string }> = [
    { value: 'square', label: 'Square', icon: '▢' },
    { value: 'circle', label: 'Circle', icon: '●' },
  ];

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-accent-primary" />
          <h4 className="text-sm font-semibold text-text-primary">LED Preview</h4>
        </div>
        <Button variant="ghost" size="sm" onClick={resetToDefaults} className="text-xs">
          Reset
        </Button>
      </div>

      {/* Shape Selector */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-text-primary">Shape</label>
        <div className="flex gap-2">
          {shapes.map(({ value, label, icon }) => (
            <button
              key={value}
              onClick={() => setShape(value)}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                settings.shape === value
                  ? 'bg-accent-primary text-black'
                  : 'bg-bg-elevated hover:bg-border-default text-text-primary'
              }`}
              title={label}
            >
              {icon} {label}
            </button>
          ))}
        </div>
      </div>

      {/* Size Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-text-primary">LED Size</label>
          <span className="text-sm font-mono text-accent-primary">{settings.size}px</span>
        </div>
        <Slider
          value={[settings.size]}
          onValueChange={(value) => setSize(value[0])}
          min={4}
          max={24}
          step={1}
          className="w-full"
        />
      </div>

      {/* Spacing Slider */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-text-primary">LED Spacing</label>
          <span className="text-sm font-mono text-accent-primary">{settings.spacing}px</span>
        </div>
        <Slider
          value={[settings.spacing]}
          onValueChange={(value) => setSpacing(value[0])}
          min={1}
          max={8}
          step={1}
          className="w-full"
        />
      </div>

      {/* Glow Toggle */}
      <div className="flex items-center justify-between p-2 rounded-md bg-bg-panel">
        <label className="text-sm font-medium text-text-primary">Glow Effect</label>
        <button
          onClick={() => setShowGlow(!settings.showGlow)}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            settings.showGlow ? 'bg-accent-primary text-black' : 'bg-bg-elevated text-text-secondary'
          }`}
        >
          {settings.showGlow ? 'On' : 'Off'}
        </button>
      </div>

      {/* Glow Intensity Slider */}
      {settings.showGlow && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-text-primary">Glow Intensity</label>
            <span className="text-sm font-mono text-accent-primary">{settings.glowIntensity}%</span>
          </div>
          <Slider
            value={[settings.glowIntensity]}
            onValueChange={(value) => setGlowIntensity(value[0])}
            min={0}
            max={100}
            step={5}
            className="w-full"
          />
        </div>
      )}
    </div>
  );
}

export default LEDPreviewSettings;
