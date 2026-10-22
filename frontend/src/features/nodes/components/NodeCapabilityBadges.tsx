interface NodeCapabilityBadgesProps {
  capabilities: string[];
  deviceCapabilities?: string[];
}

export function NodeCapabilityBadges({
  capabilities,
  deviceCapabilities = [],
}: NodeCapabilityBadgesProps): JSX.Element {
  const allCapabilities = [...capabilities, ...deviceCapabilities];

  if (allCapabilities.length === 0) {
    return <span className="text-xs text-gray-500">No capabilities reported</span>;
  }

  return (
    <ul className="flex flex-wrap gap-1">
      {allCapabilities.map((capability) => (
        <li
          key={capability}
          className="text-xs bg-gray-700 px-2 py-1 rounded font-mono"
        >
          {capability}
        </li>
      ))}
    </ul>
  );
}
