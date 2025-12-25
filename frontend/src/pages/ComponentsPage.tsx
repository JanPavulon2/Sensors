import { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Slider } from '@/shared/ui/slider';
import { Switch } from '@/shared/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu';
import { HexColorPicker } from 'react-colorful';
import { StateViewer } from '@/shared/components/dev';
import { Led, LedStrip } from '@/shared/components/leds';
import { Logger } from '@/features/logger/components';

export function ComponentsPage(): JSX.Element {
  const [sliderValue, setSliderValue] = useState([50]);
  const [switchEnabled, setSwitchEnabled] = useState(true);
  const [colorValue, setColorValue] = useState('#00E5FF');
  const [inputValue, setInputValue] = useState('');

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2">Component Showcase</h1>
        <p className="text-text-secondary">
          All available UI components and controls for building the Diuna interface
        </p>
      </div>

      {/* Buttons */}
      <Card>
        <CardHeader>
          <CardTitle>Buttons</CardTitle>
          <CardDescription>Various button variants and states</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button>Default Button</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
            <Button disabled>Disabled</Button>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button size="sm">Small</Button>
            <Button size="lg">Large</Button>
          </div>
        </CardContent>
      </Card>

      {/* Cards */}
      <Card>
        <CardHeader>
          <CardTitle>Cards</CardTitle>
          <CardDescription>Card component with different content layouts</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-muted">
              <CardHeader>
                <CardTitle className="text-lg">Zone: Floor Strip</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-8 bg-accent-primary rounded" />
                <div className="text-sm">
                  <p className="text-text-secondary">Status: Active</p>
                  <p className="text-text-secondary">Pixels: 30</p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-muted">
              <CardHeader>
                <CardTitle className="text-lg">Zone: Lamp</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-8 bg-red-500 rounded" />
                <div className="text-sm">
                  <p className="text-text-secondary">Status: Inactive</p>
                  <p className="text-text-secondary">Pixels: 20</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Inputs & Labels */}
      <Card>
        <CardHeader>
          <CardTitle>Input & Label</CardTitle>
          <CardDescription>Text input with label styling</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="zone-name">Zone Name</Label>
            <Input
              id="zone-name"
              placeholder="Enter zone name"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="brightness">Brightness</Label>
            <Input
              id="brightness"
              type="number"
              min="0"
              max="255"
              placeholder="0-255"
            />
          </div>
        </CardContent>
      </Card>

      {/* Sliders */}
      <Card>
        <CardHeader>
          <CardTitle>Slider</CardTitle>
          <CardDescription>Brightness and control sliders</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Brightness</Label>
              <span className="text-sm font-medium text-accent-primary">
                {sliderValue[0]}%
              </span>
            </div>
            <Slider
              value={sliderValue}
              onValueChange={setSliderValue}
              max={100}
              step={1}
              className="w-full"
            />
          </div>

          <div className="space-y-4">
            <Label>Speed Control</Label>
            <Slider defaultValue={[50]} max={100} step={1} className="w-full" />
          </div>
        </CardContent>
      </Card>

      {/* Switches */}
      <Card>
        <CardHeader>
          <CardTitle>Switch</CardTitle>
          <CardDescription>Toggle controls for zones and features</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Label>Floor Strip</Label>
              <p className="text-sm text-text-secondary">Enable zone</p>
            </div>
            <Switch checked={switchEnabled} onCheckedChange={setSwitchEnabled} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Lamp</Label>
              <p className="text-sm text-text-secondary">Enable zone</p>
            </div>
            <Switch defaultChecked={false} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Animation Running</Label>
              <p className="text-sm text-text-secondary">Status indicator</p>
            </div>
            <Switch defaultChecked={true} disabled />
          </div>
        </CardContent>
      </Card>

      {/* Color Picker */}
      <Card>
        <CardHeader>
          <CardTitle>Color Picker</CardTitle>
          <CardDescription>Select colors for zones and effects</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-start">
            <div className="space-y-2">
              <Label>Select Color</Label>
              <HexColorPicker color={colorValue} onChange={setColorValue} />
            </div>

            <div className="space-y-2">
              <Label>Preview</Label>
              <div className="space-y-2">
                <div
                  className="w-32 h-32 rounded-lg border-2 border-border-default shadow-lg"
                  style={{ backgroundColor: colorValue }}
                />
                <div className="text-sm font-mono text-text-secondary">{colorValue}</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Tabs</CardTitle>
          <CardDescription>Tab navigation for organizing content</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="tab1" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="tab1">RGB Mode</TabsTrigger>
              <TabsTrigger value="tab2">HSV Mode</TabsTrigger>
              <TabsTrigger value="tab3">Presets</TabsTrigger>
            </TabsList>

            <TabsContent value="tab1" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Red</Label>
                <Slider defaultValue={[255]} max={255} />
              </div>
              <div className="space-y-2">
                <Label>Green</Label>
                <Slider defaultValue={[0]} max={255} />
              </div>
              <div className="space-y-2">
                <Label>Blue</Label>
                <Slider defaultValue={[0]} max={255} />
              </div>
            </TabsContent>

            <TabsContent value="tab2" className="space-y-4 mt-4">
              <p className="text-text-secondary">HSV (Hue, Saturation, Value) color mode</p>
              <div className="space-y-2">
                <Label>Hue (0-360°)</Label>
                <Slider defaultValue={[0]} max={360} />
              </div>
              <div className="space-y-2">
                <Label>Saturation (0-100%)</Label>
                <Slider defaultValue={[100]} max={100} />
              </div>
              <div className="space-y-2">
                <Label>Value (0-100%)</Label>
                <Slider defaultValue={[100]} max={100} />
              </div>
            </TabsContent>

            <TabsContent value="tab3" className="space-y-4 mt-4">
              <div className="grid grid-cols-4 gap-2">
                {['#FF0000', '#00FF00', '#0000FF', '#FFFF00'].map((color) => (
                  <button
                    key={color}
                    className="w-full h-12 rounded-md border-2 border-border-default hover:border-accent-primary transition-colors"
                    style={{ backgroundColor: color }}
                    title={color}
                  />
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Dialog */}
      <Card>
        <CardHeader>
          <CardTitle>Dialog</CardTitle>
          <CardDescription>Modal dialogs for confirmations and forms</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Dialog>
            <DialogTrigger asChild>
              <Button>Open Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Start Animation</DialogTitle>
                <DialogDescription>
                  Choose an animation and configure its parameters below.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="animation">Animation</Label>
                  <Input id="animation" placeholder="Select animation..." />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="speed">Speed</Label>
                  <Slider defaultValue={[50]} max={100} />
                </div>

                <div className="flex gap-2 justify-end">
                  <Button variant="outline">Cancel</Button>
                  <Button>Start Animation</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      {/* Dropdown Menu */}
      <Card>
        <CardHeader>
          <CardTitle>Dropdown Menu</CardTitle>
          <CardDescription>Context menus and action dropdowns</CardDescription>
        </CardHeader>
        <CardContent>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">Zone Actions</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem>Edit Zone</DropdownMenuItem>
              <DropdownMenuItem>Duplicate Zone</DropdownMenuItem>
              <DropdownMenuItem>Reset Colors</DropdownMenuItem>
              <DropdownMenuItem className="text-destructive">Delete Zone</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardContent>
      </Card>

      {/* Status Indicators */}
      <Card>
        <CardHeader>
          <CardTitle>Status Indicators</CardTitle>
          <CardDescription>Visual feedback for system status</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-success rounded-full animate-pulse" />
            <span className="text-sm">System connected</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-warning rounded-full animate-pulse" />
            <span className="text-sm">Reconnecting...</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-error rounded-full animate-pulse" />
            <span className="text-sm">Connection lost</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-3 h-3 bg-accent-primary rounded-full" />
            <span className="text-sm">Active animation running</span>
          </div>
        </CardContent>
      </Card>

      {/* Design System Colors */}
      <Card>
        <CardHeader>
          <CardTitle>Design System Colors</CardTitle>
          <CardDescription>Tailwind color palette</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <div className="h-20 bg-background border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">bg-app</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-card border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">bg-panel</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-muted border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">bg-elevated</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-accent-primary border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">accent-primary</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-success border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">success</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-warning border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">warning</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-error border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">error</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-info border border-border rounded" />
              <p className="text-xs font-mono text-text-tertiary">info</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* LED Diodes */}
      <Card>
        <CardHeader>
          <CardTitle>LED Diodes</CardTitle>
          <CardDescription>Individual LED representations with on/off states and colors</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Sizes */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Sizes</h3>
            <div className="flex gap-8 items-center">
              <div className="flex flex-col items-center gap-2">
                <Led color="#39ff14" isOn={true} size="sm" />
                <p className="text-xs text-text-tertiary">Small</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#39ff14" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Medium</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#39ff14" isOn={true} size="lg" />
                <p className="text-xs text-text-tertiary">Large</p>
              </div>
            </div>
          </div>

          {/* On/Off States */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">States</h3>
            <div className="flex gap-12 items-center">
              <div className="flex flex-col items-center gap-2">
                <Led color="#39ff14" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">On</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#39ff14" isOn={false} size="md" />
                <p className="text-xs text-text-tertiary">Off</p>
              </div>
            </div>
          </div>

          {/* Different Colors */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Colors</h3>
            <div className="flex flex-wrap gap-6 items-center">
              <div className="flex flex-col items-center gap-2">
                <Led color="#39ff14" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Matrix Green</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#FF0000" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Red</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#00FF00" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Green</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#0000FF" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Blue</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#FFFF00" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Yellow</p>
              </div>
              <div className="flex flex-col items-center gap-2">
                <Led color="#FF00FF" isOn={true} size="md" />
                <p className="text-xs text-text-tertiary">Magenta</p>
              </div>
            </div>
          </div>

          {/* Brightness Levels */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Brightness Levels</h3>
            <div className="flex gap-4 items-center">
              {[255, 200, 150, 100, 50, 25].map((brightness) => (
                <div key={brightness} className="flex flex-col items-center gap-2">
                  <Led color="#39ff14" isOn={true} size="md" brightness={brightness} />
                  <p className="text-xs text-text-tertiary">{Math.round((brightness / 255) * 100)}%</p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* LED Strips */}
      <Card>
        <CardHeader>
          <CardTitle>LED Strips</CardTitle>
          <CardDescription>Multiple LEDs in series displaying animations and states</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Horizontal Strip - Rainbow */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Horizontal Strip - Rainbow</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={[
                  { color: '#FF0000', isOn: true },
                  { color: '#FF7F00', isOn: true },
                  { color: '#FFFF00', isOn: true },
                  { color: '#00FF00', isOn: true },
                  { color: '#0000FF', isOn: true },
                  { color: '#4B0082', isOn: true },
                  { color: '#9400D3', isOn: true },
                ]}
                size="md"
                orientation="horizontal"
                gap="xs"
              />
            </div>
          </div>

          {/* Horizontal Strip - Pattern */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Horizontal Strip - On/Off Pattern</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={[
                  { color: '#39ff14', isOn: true },
                  { color: '#39ff14', isOn: false },
                  { color: '#39ff14', isOn: true },
                  { color: '#39ff14', isOn: false },
                  { color: '#39ff14', isOn: true },
                  { color: '#39ff14', isOn: false },
                  { color: '#39ff14', isOn: true },
                  { color: '#39ff14', isOn: false },
                ]}
                size="md"
                orientation="horizontal"
                gap="xs"
              />
            </div>
          </div>

          {/* Vertical Strip - 12 LEDs */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Vertical Strip - 12 LEDs</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={Array.from({ length: 12 }, (_, i) => ({
                  color: '#39ff14',
                  isOn: i < 8,
                  brightness: 255 - (i * 20),
                }))}
                size="sm"
                orientation="vertical"
                gap="xs"
              />
            </div>
          </div>

          {/* Horizontal Strip - With Labels */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Strip with Pixel Indices</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={Array.from({ length: 8 }, (_, i) => ({
                  color: `hsl(${(i * 45) % 360}, 100%, 50%)`,
                  isOn: true,
                }))}
                size="md"
                orientation="horizontal"
                gap="sm"
                showLabels={true}
              />
            </div>
          </div>

          {/* Horizontal Strip - Gradient */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">Strip - Brightness Gradient</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={Array.from({ length: 20 }, (_, i) => ({
                  color: '#39ff14',
                  isOn: true,
                  brightness: Math.round(255 * (i / 19)),
                }))}
                size="sm"
                orientation="horizontal"
                gap="none"
              />
            </div>
          </div>

          {/* Compact Matrix - 8x8 Grid */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">LED Matrix - 8x8 Grid</h3>
            <div className="flex justify-center bg-secondary p-6 rounded">
              <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(8, 1fr)' }}>
                {Array.from({ length: 64 }, (_, i) => (
                  <Led
                    key={i}
                    color="#39ff14"
                    isOn={Math.random() > 0.3}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Compact Matrix - 16x4 Grid */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">LED Matrix - 16x4 Grid (Like Panel)</h3>
            <div className="flex justify-center bg-secondary p-6 rounded">
              <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(16, 1fr)' }}>
                {Array.from({ length: 64 }, (_, i) => (
                  <Led
                    key={i}
                    color={`hsl(${(i % 16) * 22.5}, 100%, 50%)`}
                    isOn={true}
                    size="sm"
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Circular Pattern */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">LED Circle - Rotating Pattern</h3>
            <div className="flex justify-center bg-secondary p-8 rounded">
              <div
                style={{
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '280px',
                  height: '280px',
                  gap: '8px',
                }}
              >
                {Array.from({ length: 12 }, (_, i) => (
                  <div
                    key={i}
                    style={{
                      position: 'absolute',
                      width: '32px',
                      height: '32px',
                      left: '50%',
                      top: '50%',
                      transform: `rotate(${(i * 30) - 96}deg) translateY(-80px)`,
                      marginLeft: '-16px',
                      marginTop: '-16px',
                    }}
                  >
                    <Led color="#39ff14" isOn={true} size="lg" />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Pulsing Wave Effect */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">LED Wave - Pulsing Effect</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={Array.from({ length: 16 }, (_, i) => {
                  const phase = (i % 4) / 4;
                  return {
                    color: '#39ff14',
                    isOn: true,
                    brightness: Math.round(128 + 127 * Math.sin(phase * Math.PI)),
                  };
                })}
                size="md"
                orientation="horizontal"
                gap="sm"
              />
            </div>
          </div>

          {/* Random Noise Pattern */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">LED Noise - Random Pattern</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={Array.from({ length: 24 }, () => ({
                  color: ['#39ff14', '#FF0000', '#0000FF', '#FFFF00'][Math.floor(Math.random() * 4)],
                  isOn: Math.random() > 0.2,
                  brightness: Math.floor(Math.random() * 256),
                }))}
                size="sm"
                orientation="horizontal"
                gap="xs"
              />
            </div>
          </div>

          {/* Dual Color Strip */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-text-primary">LED Strip - Dual Color Chase</h3>
            <div className="flex justify-center bg-secondary p-4 rounded">
              <LedStrip
                colors={Array.from({ length: 12 }, (_, i) => ({
                  color: i % 2 === 0 ? '#39ff14' : '#FF00FF',
                  isOn: true,
                }))}
                size="md"
                orientation="horizontal"
                gap="xs"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* State Viewer (Debug) */}
      <Card>
        <CardHeader>
          <CardTitle>Application State</CardTitle>
          <CardDescription>Real-time view of Zustand store state</CardDescription>
        </CardHeader>
        <CardContent>
          <StateViewer />
        </CardContent>
      </Card>

      {/* Real-Time Logger */}
      <Logger enabled={true} maxHeight="h-[500px]" />
    </div>
  );
}

export default ComponentsPage;
