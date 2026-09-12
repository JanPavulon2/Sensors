import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { setNodesSnapshot, updateNodeSnapshot, useNodes } from "./nodes.store";
import type { NodeSnapshot } from "@/shared/types/domain/node";

function makeNode(overrides: Partial<NodeSnapshot> = {}): NodeSnapshot {
  return {
    instance_id: "1",
    external_node_id: "AA:BB:CC:DD:EE:FF",
    node_type: "ESP32",
    address: "10.0.0.5",
    command_port: 8080,
    firmware: "diuna-esp32-poc",
    capabilities: ["render_output"],
    online: true,
    last_seen: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("nodes.store", () => {
  it("returns an empty array before any snapshot arrives", () => {
    const { result } = renderHook(() => useNodes());
    expect(Array.isArray(result.current)).toBe(true);
  });

  it("replaces the full node list on setNodesSnapshot", () => {
    const { result } = renderHook(() => useNodes());

    act(() => {
      setNodesSnapshot([makeNode()]);
    });

    expect(result.current).toHaveLength(1);
    expect(result.current[0].external_node_id).toBe("AA:BB:CC:DD:EE:FF");
  });

  it("upserts a single node on updateNodeSnapshot without dropping others", () => {
    const { result } = renderHook(() => useNodes());

    act(() => {
      setNodesSnapshot([makeNode({ external_node_id: "AA" }), makeNode({ external_node_id: "BB" })]);
    });
    act(() => {
      updateNodeSnapshot(makeNode({ external_node_id: "AA", online: false }));
    });

    expect(result.current).toHaveLength(2);
    const nodeA = result.current.find((n) => n.external_node_id === "AA");
    expect(nodeA?.online).toBe(false);
  });
});
