import { socket } from '@/realtime/socket';
import {
  setZonesSnapshot,
  updateZoneSnapshot,
} from './zones.store';
import type { ZoneSnapshot } from '@/shared/types/domain/zone';

socket.on('zones.snapshot', (zones: ZoneSnapshot[]) => {
  setZonesSnapshot(zones);
});

socket.on('zone.snapshot', (zone: ZoneSnapshot) => {
  updateZoneSnapshot(zone);
});