import { useEffect, useState } from "react";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useNodes, setNodesSnapshot } from "@/features/nodes/realtime/nodes.store";
import { useNodesQuery, useRemoteZonesQuery } from "@/features/nodes/api/queries";
import { NodeCard } from "./NodeCard";
import { FixtureControls } from "./FixtureControls";
import { FixtureEditForm } from "./FixtureEditForm";
import type { NodeSnapshot } from "@/shared/types/domain/node";

function NodeZonesSection({ node }: { node: NodeSnapshot }): JSX.Element {
  const { data: allZones, isLoading, refetch } = useRemoteZonesQuery();
  const [editingFixtureId, setEditingFixtureId] = useState<string | null>(null);

  if (isLoading) {
    return <div className="text-xs text-gray-400 pl-4">Loading zones...</div>;
  }

  const zones = (allZones ?? []).filter((zone) => zone.node_id === node.external_node_id);

  if (zones.length === 0) {
    return <div className="text-xs text-gray-500 pl-4">No zones configured for this node</div>;
  }

  return (
    <div className="pl-4 space-y-2">
      {zones.map((zone) => (
        <div key={zone.zone_id} className="space-y-2">
          <FixtureControls zone={zone} />
          {zone.fixtures.map((fixture) =>
            editingFixtureId === fixture.id ? (
              <FixtureEditForm
                key={fixture.id}
                fixture={fixture}
                onSaved={() => {
                  setEditingFixtureId(null);
                  refetch();
                }}
              />
            ) : (
              <Button
                key={fixture.id}
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => setEditingFixtureId(fixture.id)}
              >
                Edit {fixture.label}
              </Button>
            )
          )}
        </div>
      ))}
    </div>
  );
}

function ExpandableNode({ node }: { node: NodeSnapshot }): JSX.Element {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 mt-4"
          onClick={() => setExpanded((prev) => !prev)}
          aria-label={expanded ? "Collapse zones" : "Expand zones"}
        >
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </Button>
        <div className="flex-1">
          <NodeCard node={node} />
        </div>
      </div>
      {expanded && <NodeZonesSection node={node} />}
    </div>
  );
}

export function NodeList(): JSX.Element {
  const nodes = useNodes();
  const { data: initialNodes, isLoading, error } = useNodesQuery();

  // Seed the realtime store from the initial REST fetch so the page isn't
  // empty while waiting for the first Socket.IO snapshot - same pattern
  // zones/hooks/useZones.ts uses for the zones feature.
  useEffect(() => {
    if (initialNodes) {
      setNodesSnapshot(initialNodes);
    }
  }, [initialNodes]);

  if (isLoading && nodes.length === 0) {
    return <Card className="p-8 text-center text-gray-400">Loading nodes...</Card>;
  }

  if (error) {
    return <Card className="p-8 text-center text-red-400">Failed to load nodes: {error.message}</Card>;
  }

  if (nodes.length === 0) {
    return <Card className="p-8 text-center text-gray-400">No nodes have connected yet</Card>;
  }

  return (
    <div className="space-y-3">
      {nodes.map((node) => (
        <ExpandableNode key={node.external_node_id} node={node} />
      ))}
    </div>
  );
}
