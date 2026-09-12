import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NodeCard } from "./NodeCard";
import * as nodeCommands from "@/features/nodes/api/node.commands";
import type { NodeSnapshot } from "@/shared/types/domain/node";

const onlineNode: NodeSnapshot = {
  instance_id: "1",
  external_node_id: "AA:BB:CC:DD:EE:FF",
  node_type: "ESP32",
  address: "10.0.0.5",
  command_port: 8080,
  firmware: "diuna-esp32-poc",
  capabilities: ["render_output", "command_execution"],
  online: true,
  last_seen: "2026-01-01T00:00:00Z",
};

describe("NodeCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows connection properties for an online node", () => {
    render(<NodeCard node={onlineNode} />);

    expect(screen.getByText("10.0.0.5:8080")).toBeInTheDocument();
    expect(screen.getByText("diuna-esp32-poc")).toBeInTheDocument();
    expect(screen.getByText(/online/i)).toBeInTheDocument();
    expect(screen.getByText("render_output")).toBeInTheDocument();
  });

  it("shows an offline indicator for an offline node", () => {
    render(<NodeCard node={{ ...onlineNode, online: false }} />);

    expect(screen.getByText(/offline/i)).toBeInTheDocument();
  });

  it("sends an identify command when the Identify button is clicked", async () => {
    const sendNodeCommandSpy = vi.spyOn(nodeCommands, "sendNodeCommand").mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<NodeCard node={onlineNode} />);
    await user.click(screen.getByRole("button", { name: /identify/i }));

    expect(sendNodeCommandSpy).toHaveBeenCalledWith("AA:BB:CC:DD:EE:FF", "identify", {});
  });
});
