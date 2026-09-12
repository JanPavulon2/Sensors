/**
 * Nodes Page
 *
 * Shows every connected remote node (ESP32) with its connection properties
 * (address, firmware, capabilities, online state) and, for nodes with
 * addressable strips, their remote zone controls (Phase 6).
 */

import { NodeList } from "@/features/nodes/components";

export function Nodes(): JSX.Element {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-4xl font-bold mb-2">Nodes</h1>
        <p className="text-gray-400">Connected ESP32 nodes and their remote LED zones</p>
      </div>

      <NodeList />
    </div>
  );
}

export default Nodes;
