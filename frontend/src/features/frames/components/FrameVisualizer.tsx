import { useState } from 'react';
// OLD: import { useEffect, useState } from 'react';
import { Play, Pause, Square, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import '../realtime/frames.socket'; // side-effect: socket auto-connects (autoConnect: true)
// OLD: import { connectFrameStream, disconnectFrameStream } from '../realtime/frames.socket';
import { FrameMetadata } from './FrameMetadata';
import { AllZonesView } from './AllZonesView';
import { FpsControl } from './FpsControl';
import { api } from '@/shared/api/client';

type StreamState = 'stopped' | 'playing' | 'paused';

export function FrameVisualizer() {
  const [streamState, setStreamState] = useState<StreamState>('stopped');
  const [isCollapsed, setIsCollapsed] = useState(true);

  // OLD: connection managed here — now auto-connected via frames.socket.ts autoConnect: true
  // Play/Pause/Stop only control visibility of AllZonesView below
  // useEffect(() => {
  //   if (streamState === 'playing') {
  //     connectFrameStream();
  //   } else {
  //     disconnectFrameStream();
  //   }
  //   return () => disconnectFrameStream();
  // }, [streamState]);

  const handlePlay = () => {
    setStreamState('playing');
    setIsCollapsed(false);
  };

  const handlePause = () => {
    setStreamState('paused');
  };

  const handleStop = () => {
    setStreamState('stopped');
    setIsCollapsed(true);
  };

  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleFpsChange = async (fps: number) => {
    try {
      await api.put('/v1/frames/fps', { target_fps: fps });
      console.log(`[FrameVisualizer] Stream FPS updated to ${fps}`);
    } catch (error) {
      console.error('[FrameVisualizer] Failed to update FPS:', error);
    }
  };

  const isActive = streamState !== 'stopped';

  return (
    <Card className="bg-bg-card">
      <CardHeader>
        <div className="flex flex-col gap-4">
          {/* Title and Metadata Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CardTitle>Live Frame Stream</CardTitle>
              {streamState === 'playing' && <FrameMetadata />}
            </div>
          </div>

          {/* Controls Row - FPS Slider + Transport Controls */}
          <div className="flex items-center justify-between gap-4">
            {/* FPS Control */}
            {isActive && (
              <div className="flex-1">
                <FpsControl initialFps={30} onFpsChange={handleFpsChange} />
              </div>
            )}

            {/* Transport Controls */}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-9 w-9"
                onClick={handleStop}
                disabled={streamState === 'stopped'}
                title="Stop"
              >
                <Square className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-9 w-9"
                onClick={handlePause}
                disabled={streamState !== 'playing'}
                title="Pause"
              >
                <Pause className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-9 w-9"
                onClick={handlePlay}
                disabled={streamState === 'playing'}
                title="Play"
              >
                <Play className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>

      {isActive && (
        <CardContent><AllZonesView /></CardContent>
      )}

      {streamState === 'stopped' && (
        <CardContent>
          <p className="text-center py-6 text-text-secondary">
            Click Play to visualize real-time LED output at 30 fps
          </p>
        </CardContent>
      )}
    </Card>
  );
}
