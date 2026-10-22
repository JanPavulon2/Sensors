/**
 * Fixture Edit Form
 *
 * Edits the properties of a fitted light that no software can discover:
 * its label, and above all the physical colour of the diode or strip actually
 * installed. Only the person who wired it knows that, so it is declared here
 * and stored in the rig, exactly like an editable label.
 *
 * First piece of the graphical zone add/edit interface - see
 * docs/architecture-vnext/03-led-taxonomy.md.
 */

import { useState } from "react";
import { Card } from "@/shared/ui/card";
import { Button } from "@/shared/ui/button";
import { upsertFixtureInstance } from "@/features/nodes/api/rig.commands";
import type { FixtureInstance, WhiteProfile } from "@/shared/types/domain/node";

const WHITE_PROFILES: WhiteProfile[] = ["COLD", "WARM", "NEUTRAL", "TUNABLE"];

type RGB = [number, number, number];

function toHex([red, green, blue]: RGB): string {
  return `#${[red, green, blue].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

function fromHex(hex: string): RGB {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
}

interface FixtureEditFormProps {
  fixture: FixtureInstance;
  onSaved?: () => void;
}

export function FixtureEditForm({ fixture, onSaved }: FixtureEditFormProps): JSX.Element {
  const [label, setLabel] = useState(fixture.label);
  const [nominalColor, setNominalColor] = useState<RGB>(
    fixture.config.nominal_color ?? [255, 255, 255]
  );
  const [whiteProfile, setWhiteProfile] = useState<WhiteProfile | "">(
    fixture.config.white_profile ?? ""
  );
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await upsertFixtureInstance({
        id: fixture.id,
        definition_id: fixture.definition_id,
        node_id: fixture.node_id,
        label,
        nominal_color: nominalColor,
        white_profile: whiteProfile === "" ? null : whiteProfile,
        bindings: fixture.config.bindings ?? [],
      });
      onSaved?.();
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="text-sm font-semibold">Edit fixture</div>

      <div>
        <label htmlFor={`label-${fixture.id}`} className="text-xs text-gray-400 block mb-1">
          Label
        </label>
        <input
          id={`label-${fixture.id}`}
          type="text"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
        />
      </div>

      <div>
        <label htmlFor={`color-${fixture.id}`} className="text-xs text-gray-400 block mb-1">
          Physical colour of the fitted diode
        </label>
        <div className="flex items-center gap-2">
          <input
            id={`color-${fixture.id}`}
            type="color"
            value={toHex(nominalColor)}
            onChange={(event) => setNominalColor(fromHex(event.target.value))}
            className="w-10 h-8 bg-transparent border border-gray-700 rounded cursor-pointer"
          />
          <span className="text-xs text-gray-500">
            Not detectable &mdash; only you know what was wired in
          </span>
        </div>
      </div>

      <div>
        <label htmlFor={`profile-${fixture.id}`} className="text-xs text-gray-400 block mb-1">
          White profile
        </label>
        <select
          id={`profile-${fixture.id}`}
          value={whiteProfile}
          onChange={(event) => setWhiteProfile(event.target.value as WhiteProfile | "")}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
        >
          <option value="">Not specified</option>
          {WHITE_PROFILES.map((profile) => (
            <option key={profile} value={profile}>
              {profile}
            </option>
          ))}
        </select>
      </div>

      <Button size="sm" onClick={handleSave} disabled={isSaving}>
        {isSaving ? "Saving..." : "Save fixture"}
      </Button>
    </Card>
  );
}
