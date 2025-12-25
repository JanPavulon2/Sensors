/**
 * LED Strip Component
 * Displays a strip of LEDs with individual colors and states
 */

import { Led } from './Led';

interface LedStripProps {
  colors: Array<{
    color: string;
    isOn: boolean;
    brightness?: number;
  }>;
  size?: 'sm' | 'md' | 'lg';
  orientation?: 'horizontal' | 'vertical';
  gap?: 'none' | 'xs' | 'sm' | 'md';
  showLabels?: boolean;
}

const gapMap = {
  none: 'gap-0',
  xs: 'gap-1',
  sm: 'gap-2',
  md: 'gap-3',
};

export function LedStrip({
  colors,
  size = 'md',
  orientation = 'horizontal',
  gap = 'xs',
  showLabels = false,
}: LedStripProps): JSX.Element {
  const isHorizontal = orientation === 'horizontal';
  const flexDirection = isHorizontal ? 'flex-row' : 'flex-col';

  return (
    <div className={`flex ${flexDirection} ${gapMap[gap]} items-center justify-center p-4`}>
      {colors.map((item, index) => (
        <Led
          key={index}
          color={item.color}
          isOn={item.isOn}
          size={size}
          brightness={item.brightness ?? 255}
          label={showLabels ? index : undefined}
        />
      ))}
    </div>
  );
}

export default LedStrip;
