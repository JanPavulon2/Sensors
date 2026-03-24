/**
 * Zones Page
 * Dedicated page for viewing and managing LED zones
 */

import { useState } from 'react';
import { ZonesGrid, ZoneEditPanel } from '@/features/zones/components';
import { useZones } from '@/features/zones/hooks';

export function Zones(): JSX.Element {
    // Zone detail panel state
    const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

    // Real-time zone updates via Socket.IO
    const zones = useZones();

    // Find selected zone and its index
    const selectedZone = zones.find(z => z.id === selectedZoneId);
    const selectedZoneIndex = selectedZone ? zones.indexOf(selectedZone) : 0;

    // Navigation handlers for detail panel
    const handlePrevZone = () => {
        if (selectedZoneIndex > 0) {
            setSelectedZoneId(zones[selectedZoneIndex - 1].id);
        }
    };

    const handleNextZone = () => {
        if (selectedZoneIndex < zones.length - 1) {
            setSelectedZoneId(zones[selectedZoneIndex + 1].id);
        }
    };

    const handleClosePanel = () => {
        setSelectedZoneId(null);
    };

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Zones</h1>
                <p className="text-text-secondary mt-2">
                    View and manage your LED zones
                </p>
            </div>

            {/* Zones Grid */}
            <ZonesGrid onSelectZone={setSelectedZoneId} />

            {/* Zone Edit Panel */}
            {selectedZone && (
                <ZoneEditPanel
                    zone={selectedZone}
                    currentIndex={selectedZoneIndex}
                    totalZones={zones.length}
                    onClose={handleClosePanel}
                    onPrevZone={handlePrevZone}
                    onNextZone={handleNextZone}
                />
            )}
        </div>
    );
}

export default Zones;