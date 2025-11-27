/**
 * LED Diode Component
 * Displays a single LED with realistic glow effect
 */

interface LedProps {
  color?: string; // Hex color when LED is on (#RRGGBB)
  isOn: boolean;
  size?: 'sm' | 'md' | 'lg'; // 8px, 16px, 24px
  label?: string | number; // Optional label (pixel index, etc)
  brightness?: number; // 0-255
}

const sizeMap = {
  sm: 'w-2 h-2',
  md: 'w-4 h-4',
  lg: 'w-6 h-6',
};

const labelSizeMap = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base',
};

export function Led({
  color = '#39ff14',
  isOn,
  size = 'md',
  label,
  brightness = 255,
}: LedProps): JSX.Element {
  // Adjust color brightness
  const adjustBrightness = (hex: string, bright: number): string => {
    const num = parseInt(hex.slice(1), 16);
    const r = Math.round(((num >> 16) & 255) * (bright / 255));
    const g = Math.round(((num >> 8) & 255) * (bright / 255));
    const b = Math.round((num & 255) * (bright / 255));
    return `rgb(${r}, ${g}, ${b})`;
  };

  const displayColor = isOn ? adjustBrightness(color, brightness) : 'rgb(30, 30, 30)';
  const glowColor = isOn ? color : 'transparent';

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`${sizeMap[size]} rounded-full transition-all duration-200 flex-shrink-0`}
        style={{
          backgroundColor: displayColor,
          boxShadow: isOn
            ? `0 0 ${size === 'sm' ? 4 : size === 'md' ? 8 : 12}px ${glowColor},
               0 0 ${size === 'sm' ? 8 : size === 'md' ? 16 : 24}px ${glowColor}80,
               inset -1px -1px 3px rgba(0,0,0,0.5),
               inset 1px 1px 3px rgba(255,255,255,0.2)`
            : '0 0 0 1px rgb(60, 60, 60), inset -1px -1px 2px rgba(0,0,0,0.9)',
        }}
        title={isOn ? `LED On - ${color}` : 'LED Off'}
      />
      {label !== undefined && (
        <span className={`${labelSizeMap[size]} text-text-tertiary font-mono text-center`}>
          {label}
        </span>
      )}
    </div>
  );
}

export default Led;
