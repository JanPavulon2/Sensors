from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class DeviceInstance:
    """Concrete deployed device bound to a node and a definition.

    `definition_id` is a DeviceDefinition slug (str, not UUID) - definitions are
    a hand-authored catalog that appears verbatim in rig config and API payloads,
    so a readable stable id beats a generated one.

    `config` carries the deployment facts a blueprint cannot know: which GPIO
    pins this board's channels landed on, what colour diode the user actually
    fitted, which module channels drive this fixture. Blueprint-level facts
    (Module, LightFixture, Peripheral) never live here.
    """

    id: str
    definition_id: str
    node_id: str
    label: str
    config: Mapping[str, Any] = field(default_factory=dict)
