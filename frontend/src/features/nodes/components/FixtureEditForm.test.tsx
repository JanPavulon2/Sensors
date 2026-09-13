import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FixtureEditForm } from "./FixtureEditForm";
import * as rigCommands from "@/features/nodes/api/rig.commands";
import type { FixtureInstance } from "@/shared/types/domain/node";

const fixture: FixtureInstance = {
  id: "desk_diode",
  definition_id: "single_diode",
  node_id: "AA:BB",
  label: "Desk diode",
  config: {
    nominal_color: [255, 170, 80],
    white_profile: "WARM",
    bindings: [{ module_instance_id: "desk_dimmer", channel_name: "ch0", role: "SINGLE" }],
  },
  capabilities: ["switch_binary", "dimming"],
  component_type: "SINGLE_COLOR",
  component_count: 1,
  addressable_group_count: 1,
};

describe("FixtureEditForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("pre-fills the fixture's current user-declared properties", () => {
    render(<FixtureEditForm fixture={fixture} />);

    expect(screen.getByLabelText(/label/i)).toHaveValue("Desk diode");
    expect(screen.getByLabelText(/physical colour/i)).toHaveValue("#ffaa50");
    expect(screen.getByLabelText(/white profile/i)).toHaveValue("WARM");
  });

  it("saves an edited label while preserving the existing wiring", async () => {
    const upsertSpy = vi.spyOn(rigCommands, "upsertFixtureInstance").mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<FixtureEditForm fixture={fixture} />);
    await user.clear(screen.getByLabelText(/label/i));
    await user.type(screen.getByLabelText(/label/i), "Reading lamp");
    await user.click(screen.getByRole("button", { name: /save fixture/i }));

    expect(upsertSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "desk_diode",
        label: "Reading lamp",
        nominal_color: [255, 170, 80],
        bindings: [{ module_instance_id: "desk_dimmer", channel_name: "ch0", role: "SINGLE" }],
      })
    );
  });

  it("notifies the caller once the fixture is saved", async () => {
    vi.spyOn(rigCommands, "upsertFixtureInstance").mockResolvedValue(undefined);
    const onSaved = vi.fn();
    const user = userEvent.setup();

    render(<FixtureEditForm fixture={fixture} onSaved={onSaved} />);
    await user.click(screen.getByRole("button", { name: /save fixture/i }));

    expect(onSaved).toHaveBeenCalled();
  });
});
