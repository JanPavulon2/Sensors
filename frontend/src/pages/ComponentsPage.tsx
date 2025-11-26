import { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { HexColorPicker } from 'react-colorful';

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
            <Card className="bg-bg-elevated border-border-default">
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

            <Card className="bg-bg-elevated border-border-default">
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
              <div className="h-20 bg-bg-app border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">bg-app</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-bg-panel border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">bg-panel</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-bg-elevated border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">bg-elevated</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-accent-primary border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">accent-primary</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-success border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">success</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-warning border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">warning</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-error border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">error</p>
            </div>
            <div className="space-y-2">
              <div className="h-20 bg-info border border-border-default rounded" />
              <p className="text-xs font-mono text-text-tertiary">info</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default ComponentsPage;
