/**
 * Zone Detail Panel - Comprehensive zone editor
 *
 * Features:
 * - Full-sized LED preview at top
 * - Collapsible sections (Status, Color, Animation)
 * - On/off toggle, brightness slider
 * - Color controls (Hue + Preset)
 * - Animation selector (stub for Phase 3)
 * - Zone navigation (prev/next)
 */

import React, { useState } from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Slider } from '@/shared/ui/slider';
import { FullLEDPreview, type RGB, type ShapeConfig } from './FullLEDPreview';
import { ColorControlPanel, type ColorValue } from './ColorControlPanel';
import { AnimationSelector, type AnimationID } from './AnimationSelector';
import { AnimationParametersPanel } from './AnimationParametersPanel';

export interface Zone {
  id: string;
  name: string;
  pixel_count: number;
  enabled?: boolean;
  state: {
    is_on: boolean;
    animation_id?: string;
    color: ColorValue;
    brightness: number; // 0-255
  };
  mode?: AnimationID; // For display
  color?: ColorValue;
  brightness?: number;
  shapeConfig?: ShapeConfig;
}

interface ZoneDetailPanelProps {
  zone: Zone;
  currentIndex: number;
  totalZones: number;
  pixels: RGB[];
  isTogglingZone?: boolean;
  isChangingAnimation?: boolean;
  isUpdatingParameters?: boolean;
  onToggleZone?: () => void;
  onAnimationChange?: (animationId: string) => void;
  onAnimationParametersChange?: (parameters: Record<string, number | string | boolean>) => void;
  onUpdate?: (zone: Zone) => void;
  onClose: () => void;
  onPrevZone: () => void;
  onNextZone: () => void;
}

/**
 * ZoneDetailPanel Component
 * Full-featured zone editor with modal overlay
 */
export const ZoneDetailPanel: React.FC<ZoneDetailPanelProps> = ({
  zone,
  currentIndex,
  totalZones,
  pixels,
  isTogglingZone = false,
  isChangingAnimation = false,
  isUpdatingParameters = false,
  onToggleZone,
  onAnimationChange,
  onAnimationParametersChange,
  onUpdate,
  onClose,
  onPrevZone,
  onNextZone,
}) => {
  // Collapsible section states
  const [expandedSections, setExpandedSections] = useState({
    status: true,
    color: true,
    animation: false,
  });

  // Animation state
  const [animationParameters, setAnimationParameters] = useState<Record<string, number | string | boolean>>({});

  // Toggle section
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Handle zone updates
  const handleToggle = () => {
    onToggleZone?.();
  };

  const handleBrightnessChange = (value: number[]) => {
    onUpdate?.({ ...zone, brightness: value[0] });
  };

  const handleModeChange = (mode: Zone['mode']) => {
    if (mode && onAnimationChange) {
      onAnimationChange(mode as string);
    } else {
      onUpdate?.({ ...zone, mode });
    }
  };

  const handleColorChange = (color: ColorValue) => {
    onUpdate?.({ ...zone, color });
  };

  const handleColorBrightnessChange = (brightness: number) => {
    onUpdate?.({ ...zone, brightness });
  };

  const brightnessPercent = zone.brightness ? Math.round((zone.brightness / 255) * 100) : 0;

  return (
    <>
      {/* Modal Overlay */}
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-bg-panel shadow-lg z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border-default">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-text-primary">{zone.name}</h2>
            <p className="text-sm text-text-tertiary mt-1">
              {zone.pixel_count} pixels • {zone.mode}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 hover:bg-bg-elevated"
            aria-label="Close panel"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Live Preview */}
          <div className="p-6 border-b border-border-default">
            <h3 className="text-sm font-medium text-text-primary mb-3">Live Preview</h3>
            <FullLEDPreview
              pixels={pixels}
              pixelCount={zone.pixel_count}
              shape={zone.shapeConfig}
              brightness={zone.brightness ?? 255}
              animationMode={zone.mode}
              containerHeight={100}
            />
          </div>

          {/* Status Section */}
          <div className="border-b border-border-default">
            <button
              onClick={() => toggleSection('status')}
              className="w-full flex items-center justify-between p-4 hover:bg-bg-elevated transition-colors"
            >
              <span className={`text-sm font-medium text-text-primary flex items-center gap-2 ${expandedSections.status ? '' : 'text-text-secondary'}`}>
                <span>{expandedSections.status ? '▼' : '▶'}</span>
                Status
              </span>
            </button>

            {expandedSections.status && (
              <div className="px-4 pb-4 space-y-4">
                {/* On/Off Toggle */}
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-text-primary">Enable Zone</label>
                  <button
                    onClick={handleToggle}
                    disabled={isTogglingZone}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      zone.enabled
                        ? 'bg-accent-primary text-bg-app'
                        : 'bg-border-default text-text-secondary'
                    } ${isTogglingZone ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {isTogglingZone ? '⏳' : zone.enabled ? '✓ On' : '✕ Off'}
                  </button>
                </div>

                {/* Mode Selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-text-primary">Animation Mode</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['STATIC', 'BREATHE', 'COLOR_FADE', 'COLOR_CYCLE', 'SNAKE', 'COLOR_SNAKE'] as const).map(
                      (mode) => (
                        <button
                          key={mode}
                          onClick={() => handleModeChange(mode)}
                          disabled={isChangingAnimation}
                          className={`px-2 py-2 rounded text-xs font-medium transition-colors ${
                            zone.mode === mode
                              ? 'bg-accent-primary text-bg-app'
                              : 'bg-bg-elevated text-text-secondary hover:bg-border-default'
                          } ${isChangingAnimation ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                          {mode === 'STATIC' && '📍'}
                          {mode === 'BREATHE' && '💨'}
                          {mode === 'COLOR_FADE' && '🌅'}
                          {mode === 'COLOR_CYCLE' && '🔄'}
                          {mode === 'SNAKE' && '🐍'}
                          {mode === 'COLOR_SNAKE' && '🌈'}
                          <span className="hidden sm:inline ml-1">{mode}</span>
                        </button>
                      )
                    )}
                  </div>
                </div>

                {/* Brightness Slider */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-text-primary">Brightness</label>
                    <span className="text-sm font-mono text-accent-primary">{brightnessPercent}%</span>
                  </div>
                  <Slider
                    value={[zone.brightness ?? 255]}
                    onValueChange={handleBrightnessChange}
                    max={255}
                    step={1}
                    className="w-full"
                  />
                  {/* Brightness preview bar */}
                  <div
                    className="h-4 rounded border border-border-default transition-all"
                    style={{
                      background: `linear-gradient(90deg, rgba(57, 255, 20, 0.1) 0%, rgba(57, 255, 20, 0.5) 100%)`,
                      opacity: (zone.brightness ?? 255) / 255,
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Color Section */}
          <div className="border-b border-border-default">
            <button
              onClick={() => toggleSection('color')}
              className="w-full flex items-center justify-between p-4 hover:bg-bg-elevated transition-colors"
            >
              <span className={`text-sm font-medium text-text-primary flex items-center gap-2 ${expandedSections.color ? '' : 'text-text-secondary'}`}>
                <span>{expandedSections.color ? '▼' : '▶'}</span>
                Color
              </span>
            </button>

            {expandedSections.color && (
              <div className="px-4 pb-4">
                <ColorControlPanel
                  color={zone.color ?? { mode: 'HUE', hue: 0 }}
                  brightness={zone.brightness ?? 255}
                  onColorChange={handleColorChange}
                  onBrightnessChange={handleColorBrightnessChange}
                  disabled={!zone.enabled}
                />
              </div>
            )}
          </div>

          {/* Animation Section */}
          <div className="border-b border-border-default">
            <button
              onClick={() => toggleSection('animation')}
              className="w-full flex items-center justify-between p-4 hover:bg-bg-elevated transition-colors"
            >
              <span className={`text-sm font-medium text-text-primary flex items-center gap-2 ${expandedSections.animation ? '' : 'text-text-secondary'}`}>
                <span>{expandedSections.animation ? '▼' : '▶'}</span>
                Animation
              </span>
            </button>

            {expandedSections.animation && (
              <div className="px-4 pb-4 space-y-4">
                {/* Animation Selector */}
                <div className="space-y-2">
                  <p className="text-sm font-medium text-text-primary">Select Animation</p>
                  <AnimationSelector
                    selectedAnimation={zone.mode}
                    onSelect={(mode) => onUpdate?.({ ...zone, mode })}
                    disabled={!zone.enabled}
                  />
                </div>

                {/* Animation Parameters */}
                {zone.mode && zone.mode !== 'STATIC' && (
                  <div className="space-y-2 pt-2 border-t border-border-subtle">
                    <p className="text-sm font-medium text-text-primary">Parameters</p>
                    <AnimationParametersPanel
                      animationId={zone.mode as any}
                      parameters={animationParameters}
                      onParameterChange={(id, value) => {
                        const newParameters = { ...animationParameters, [id]: value };
                        setAnimationParameters(newParameters);
                        if (onAnimationParametersChange) {
                          onAnimationParametersChange(newParameters);
                        }
                      }}
                      disabled={!zone.enabled || isUpdatingParameters}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer - Navigation */}
        <div className="flex items-center justify-between p-4 border-t border-border-default bg-bg-elevated">
          <Button
            variant="outline"
            size="sm"
            onClick={onPrevZone}
            disabled={currentIndex === 0}
            className="gap-1"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </Button>

          <span className="text-sm font-medium text-text-secondary">
            {currentIndex + 1} / {totalZones}
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={onNextZone}
            disabled={currentIndex === totalZones - 1}
            className="gap-1"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </>
  );
};

export default ZoneDetailPanel;
