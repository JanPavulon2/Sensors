import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function Dashboard(): JSX.Element {
  return (
    <div className="space-y-6 max-w-6xl">
      {/* Welcome Card */}
      <Card className="bg-gradient-to-r from-bg-elevated to-bg-panel border-border-default">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-2xl">🎨</span>
            Welcome to Diuna
          </CardTitle>
          <CardDescription>Real-time LED animation design and control</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-text-secondary mb-4">
            Connect to your LED control system backend to start designing, controlling, and animating your
            LED strips. Check out the Components page to see all available UI controls.
          </p>
          <Button>Getting Started</Button>
        </CardContent>
      </Card>

      {/* System Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Connection</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-error rounded-full animate-pulse" />
              <span className="text-sm text-text-secondary">Disconnected</span>
            </div>
            <Button variant="outline" size="sm" className="mt-4 w-full">
              Connect
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <p className="text-text-secondary">FPS: <span className="text-text-primary font-medium">--</span></p>
              <p className="text-text-secondary">Latency: <span className="text-text-primary font-medium">--ms</span></p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Active Zones</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-accent-primary">0</div>
            <p className="text-xs text-text-tertiary mt-1">No zones loaded</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Start Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Start</CardTitle>
          <CardDescription>Get up and running in 3 steps</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="step1" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="step1">1. Connect</TabsTrigger>
              <TabsTrigger value="step2">2. Configure</TabsTrigger>
              <TabsTrigger value="step3">3. Control</TabsTrigger>
            </TabsList>

            <TabsContent value="step1" className="space-y-4 mt-4">
              <div className="space-y-2">
                <h4 className="font-medium">Connect to Backend</h4>
                <p className="text-sm text-text-secondary">
                  Go to Settings and configure your backend API and WebSocket URLs. Make sure your Diuna backend
                  is running and accessible.
                </p>
                <Button size="sm" variant="outline">
                  Open Settings
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="step2" className="space-y-4 mt-4">
              <div className="space-y-2">
                <h4 className="font-medium">Configure Your Zones</h4>
                <p className="text-sm text-text-secondary">
                  Once connected, your LED zones will appear in the sidebar. Configure colors, brightness, and
                  animations for each zone.
                </p>
              </div>
            </TabsContent>

            <TabsContent value="step3" className="space-y-4 mt-4">
              <div className="space-y-2">
                <h4 className="font-medium">Control & Animate</h4>
                <p className="text-sm text-text-secondary">
                  Use the zone controls to set colors, adjust brightness, and run animations. All changes are
                  sent in real-time to your LED hardware.
                </p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Feature Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🎬</span> Real-time Preview
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-text-secondary">
            See LED changes instantly with 60 FPS canvas rendering. Preview animations before deploying to
            hardware.
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🎨</span> Color Control
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-text-secondary">
            Set zone colors using RGB, HSV, or preset palettes. Save favorites and create custom color schemes.
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>⚡</span> Animations
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-text-secondary">
            Choose from built-in animations like breathing, wave, rainbow cycle, and more. Customize speed and
            parameters.
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🔌</span> WebSocket Sync
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-text-secondary">
            Real-time bidirectional communication with your backend. Control hardware instantly without latency.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default Dashboard;
