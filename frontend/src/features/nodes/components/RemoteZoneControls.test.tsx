import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RemoteZoneControls } from "./RemoteZoneControls";
import * as nodeCommands from "@/features/nodes/api/node.commands";
import type { RemoteZone } from "@/shared/types/domain/node";

const zone: RemoteZone = {
  node_id: "AA:BB:CC:DD:EE:FF",
  zone_label: "esp32_strip_1",
  display_name: "Workshop Strip",
  pixel_count: 30,
  sync_group: "workshop",
  state: {
    is_on: true,
    brightness: 80,
    color: { rgb: [255, 0, 0] },
    render_mode: "STATIC",
  },
};

describe("RemoteZoneControls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the zone's display name and pixel count", () => {
    render(<RemoteZoneControls zone={zone} />);

    expect(screen.getByText("Workshop Strip")).toBeInTheDocument();
    expect(screen.getByText(/30/)).toBeInTheDocument();
  });

  it("toggles power via setRemoteZoneIsOn when the switch is clicked", async () => {
    const setIsOnSpy = vi.spyOn(nodeCommands, "setRemoteZoneIsOn").mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<RemoteZoneControls zone={zone} />);
    await user.click(screen.getByRole("switch"));

    expect(setIsOnSpy).toHaveBeenCalledWith("AA:BB:CC:DD:EE:FF", "esp32_strip_1", false);
  });
});
