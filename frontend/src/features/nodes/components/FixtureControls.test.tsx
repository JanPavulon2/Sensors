import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FixtureControls } from "./FixtureControls";
import * as rigCommands from "@/features/nodes/api/rig.commands";
import type { DeviceCapability, FixtureInstance, RemoteZone } from "@/shared/types/domain/node";

function makeFixture(overrides: Partial<FixtureInstance> = {}): FixtureInstance {
  return {
    id: "desk_diode",
    definition_id: "single_diode",
    node_id: "AA:BB",
    label: "Desk diode",
    config: { nominal_color: [255, 170, 80] },
    capabilities: ["switch_binary", "dimming"],
    component_type: "SINGLE_COLOR",
    component_count: 1,
    addressable_group_count: 1,
    ...overrides,
  };
}

function makeZone(capabilities: DeviceCapability[], overrides: Partial<RemoteZone> = {}): RemoteZone {
  return {
    zone_id: "desk",
    display_name: "Desk",
    node_id: "AA:BB",
    device_instance_ids: ["desk_diode"],
    sync_group: null,
    capabilities,
    in_sync: true,
    state: {
      is_on: true,
      brightness: 80,
      color: { rgb: [255, 170, 80] },
      render_mode: "STATIC",
    },
    fixtures: [makeFixture()],
    ...overrides,
  };
}

describe("FixtureControls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("offers no colour picker for a fixture that cannot produce colour", () => {
    render(<FixtureControls zone={makeZone(["switch_binary", "dimming"])} />);

    expect(screen.queryByLabelText(/hue/i)).not.toBeInTheDocument();
    expect(screen.getByText(/fixed colour/i)).toBeInTheDocument();
  });

  it("shows the declared physical colour of the fitted diode", () => {
    render(<FixtureControls zone={makeZone(["switch_binary", "dimming"])} />);

    expect(screen.getByLabelText("Declared physical colour")).toHaveStyle({
      backgroundColor: "rgb(255,170,80)",
    });
  });

  it("offers a colour picker once the hardware supports colour", () => {
    const rgbZone = makeZone(["switch_binary", "dimming", "color_control_rgb"], {
      fixtures: [
        makeFixture({
          component_type: "RGB",
          capabilities: ["switch_binary", "dimming", "color_control_rgb"],
        }),
      ],
    });

    render(<FixtureControls zone={rgbZone} />);

    expect(screen.queryByText(/fixed colour/i)).not.toBeInTheDocument();
  });

  it("hides the brightness slider when the fixture cannot dim", () => {
    render(<FixtureControls zone={makeZone(["switch_binary"])} />);

    expect(screen.queryByText(/brightness/i)).not.toBeInTheDocument();
  });

  it("sends the zone power state when toggled", async () => {
    const setZoneIsOnSpy = vi.spyOn(rigCommands, "setZoneIsOn").mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<FixtureControls zone={makeZone(["switch_binary", "dimming"])} />);
    await user.click(screen.getByRole("switch"));

    expect(setZoneIsOnSpy).toHaveBeenCalledWith("desk", false);
  });

  it("toggles the breathe animation", async () => {
    const setRenderModeSpy = vi
      .spyOn(rigCommands, "setZoneRenderMode")
      .mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<FixtureControls zone={makeZone(["switch_binary", "dimming"])} />);
    await user.click(screen.getByRole("button", { name: /^breathe$/i }));

    expect(setRenderModeSpy).toHaveBeenCalledWith("desk", "BREATHE");
  });

  it("warns when the device has not confirmed the state", () => {
    render(<FixtureControls zone={makeZone(["switch_binary", "dimming"], { in_sync: false })} />);

    expect(screen.getByText(/not confirmed/i)).toBeInTheDocument();
  });
});
