import { Wifi, WifiOff, Sparkles } from "lucide-react";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { cn } from "@/lib/utils";
import { sendNodeCommand } from "@/features/nodes/api/node.commands";
import { NodeCapabilityBadges } from "./NodeCapabilityBadges";
import type { NodeSnapshot } from "@/shared/types/domain/node";

interface NodeCardProps {
  node: NodeSnapshot;
}

function formatLastSeen(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString();
  } catch {
    return isoString;
  }
}

export function NodeCard({ node }: NodeCardProps): JSX.Element {
  const handleIdentify = () => {
    sendNodeCommand(node.external_node_id, "identify", {});
  };

  return (
    <Card
      className={cn(
        "p-4 border-l-4",
        node.online ? "border-l-green-400" : "border-l-gray-500"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold">{node.node_type}</span>
            <span className="text-xs font-mono bg-gray-800 px-2 py-1 rounded truncate">
              {node.external_node_id}
            </span>
          </div>

          <div className="text-sm text-gray-300 font-mono">
            {node.address}:{node.command_port}
          </div>
          <div className="text-xs text-gray-400">{node.firmware}</div>
          <div className="text-xs text-gray-500 mt-1">
            Last seen: {formatLastSeen(node.last_seen)}
          </div>

          <div className="mt-2">
            <NodeCapabilityBadges
              capabilities={node.capabilities}
              deviceCapabilities={node.declared_device_capabilities}
            />
          </div>
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0">
          <div className="flex items-center gap-1">
            {node.online ? (
              <>
                <Wifi className="w-4 h-4 text-green-400" />
                <span className="text-xs text-green-400">Online</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-gray-400" />
                <span className="text-xs text-gray-400">Offline</span>
              </>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleIdentify}
            disabled={!node.online}
          >
            <Sparkles className="w-3 h-3 mr-2" />
            Identify
          </Button>
        </div>
      </div>
    </Card>
  );
}
