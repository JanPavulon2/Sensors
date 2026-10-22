import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NodeList } from "./NodeList";
import * as nodesStore from "@/features/nodes/realtime/nodes.store";
import * as nodesQueries from "@/features/nodes/api/queries";
import type { NodeSnapshot } from "@/shared/types/domain/node";

const node: NodeSnapshot = {
  instance_id: "1",
  external_node_id: "AA:BB:CC:DD:EE:FF",
  node_type: "ESP32",
  address: "10.0.0.5",
  command_port: 8080,
  firmware: "diuna-esp32-poc",
  capabilities: ["render_output"],
  online: true,
  last_seen: "2026-01-01T00:00:00Z",
};

function renderWithQueryClient(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("NodeList", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an empty state when there are no nodes", () => {
    vi.spyOn(nodesStore, "useNodes").mockReturnValue([]);
    vi.spyOn(nodesQueries, "useNodesQuery").mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as ReturnType<typeof nodesQueries.useNodesQuery>);

    renderWithQueryClient(<NodeList />);

    expect(screen.getByText(/no nodes/i)).toBeInTheDocument();
  });

  it("renders a NodeCard for each node from the realtime store", () => {
    vi.spyOn(nodesStore, "useNodes").mockReturnValue([node]);
    vi.spyOn(nodesQueries, "useNodesQuery").mockReturnValue({
      data: [node],
      isLoading: false,
      error: null,
    } as ReturnType<typeof nodesQueries.useNodesQuery>);

    renderWithQueryClient(<NodeList />);

    expect(screen.getByText("AA:BB:CC:DD:EE:FF")).toBeInTheDocument();
  });
});
