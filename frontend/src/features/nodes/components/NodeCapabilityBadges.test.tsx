import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NodeCapabilityBadges } from "./NodeCapabilityBadges";

describe("NodeCapabilityBadges", () => {
  it("renders one badge per node capability", () => {
    render(<NodeCapabilityBadges capabilities={["render_output", "command_execution"]} />);

    expect(screen.getByText("render_output")).toBeInTheDocument();
    expect(screen.getByText("command_execution")).toBeInTheDocument();
  });

  it("renders device capabilities when provided", () => {
    render(
      <NodeCapabilityBadges
        capabilities={["render_output"]}
        deviceCapabilities={["addressable_pixels", "color_control_rgb"]}
      />
    );

    expect(screen.getByText("addressable_pixels")).toBeInTheDocument();
    expect(screen.getByText("color_control_rgb")).toBeInTheDocument();
  });

  it("renders nothing extra when there are no capabilities at all", () => {
    render(<NodeCapabilityBadges capabilities={[]} />);

    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });
});
