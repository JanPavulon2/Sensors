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
import { Switch } from '@/components/ui/switch';

export function SettingsPage(): JSX.Element {
  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2">Settings</h1>
        <p className="text-text-secondary">Configure Diuna application preferences</p>
      </div>

      {/* Backend Connection */}
      <Card>
        <CardHeader>
          <CardTitle>Backend Connection</CardTitle>
          <CardDescription>Configure API and WebSocket connections</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="api-url">API URL</Label>
            <Input
              id="api-url"
              placeholder="http://localhost:8000/api"
              defaultValue="http://localhost:8000/api"
            />
            <p className="text-xs text-text-tertiary">REST API endpoint for data operations</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="websocket-url">WebSocket URL</Label>
            <Input
              id="websocket-url"
              placeholder="ws://localhost:8000"
              defaultValue="ws://localhost:8000"
            />
            <p className="text-xs text-text-tertiary">Real-time WebSocket connection</p>
          </div>

          <Button>Save Connection Settings</Button>
        </CardContent>
      </Card>

      {/* Display Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Display Preferences</CardTitle>
          <CardDescription>Customize UI appearance and behavior</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Label>Dark Theme</Label>
              <p className="text-sm text-text-secondary">Always enabled</p>
            </div>
            <Switch defaultChecked disabled />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Show Grid</Label>
              <p className="text-sm text-text-secondary">Display reference grid in canvas</p>
            </div>
            <Switch defaultChecked={false} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Animations</Label>
              <p className="text-sm text-text-secondary">Enable smooth transitions</p>
            </div>
            <Switch defaultChecked={true} />
          </div>
        </CardContent>
      </Card>

      {/* Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Performance</CardTitle>
          <CardDescription>Optimize rendering and update frequency</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="fps-target">Target FPS</Label>
            <Input
              id="fps-target"
              type="number"
              min="30"
              max="144"
              defaultValue="60"
            />
            <p className="text-xs text-text-tertiary">Target frame rate for rendering (30-144)</p>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Hardware Acceleration</Label>
              <p className="text-sm text-text-secondary">Use GPU when available</p>
            </div>
            <Switch defaultChecked={true} />
          </div>
        </CardContent>
      </Card>

      {/* Advanced */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced</CardTitle>
          <CardDescription>Expert settings - handle with care</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <Label>Debug Mode</Label>
              <p className="text-sm text-text-secondary">Show console logs and debug info</p>
            </div>
            <Switch defaultChecked={false} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Network Logging</Label>
              <p className="text-sm text-text-secondary">Log all API requests and WebSocket events</p>
            </div>
            <Switch defaultChecked={false} />
          </div>

          <div className="space-y-2">
            <Label>Danger Zone</Label>
            <Button variant="destructive" className="w-full">
              Clear All Settings
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Save */}
      <div className="flex gap-3">
        <Button>Save All Settings</Button>
        <Button variant="outline">Reset to Defaults</Button>
      </div>
    </div>
  );
}

export default SettingsPage;
