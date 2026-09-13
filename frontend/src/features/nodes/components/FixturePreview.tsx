/**
 * Fixture Preview
 *
 * Shows what a remote fixture is actually emitting right now, using the same
 * live output_frame stream the local zone cards use. The backend animates
 * remote fixtures host-side (services/remote_fixture_animator.py) and merges
 * them into that stream keyed by fixture instance id, so a breathing ESP32
 * fixture breathes here too, and an identify blink blinks here too.
 *
 * Falls back to the fixture's declared physical colour when no frame has
 * arrived yet.
 */

import { CompactLEDPreview } from "@/features/zones/components/preview";
import { useOutputFrame } from "@/features/frames/realtime/frames.store";
import type { FixtureInstance, RemoteZoneState } from "@/shared/types/domain/node";

type RGB = [number, number, number];

interface FixturePreviewProps {
  fixture: FixtureInstance;
  state: RemoteZoneState;
  pixelCount: number;
}

export function FixturePreview({ fixture, state, pixelCount }: FixturePreviewProps): JSX.Element {
  const frame = useOutputFrame();
  const livePixels = frame?.zones[fixture.id] as RGB[] | undefined;

  const fallbackColor: RGB = fixture.config.nominal_color ?? state.color.rgb;
  const pixels = livePixels ?? Array.from({ length: pixelCount }, () => fallbackColor);

  return (
    <CompactLEDPreview
      pixels={pixels}
      pixelCount={pixelCount}
      brightness={livePixels ? 100 : state.brightness}
      animationMode={state.render_mode}
    />
  );
}
