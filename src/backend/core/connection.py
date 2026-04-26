from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """Connection between two device instance ports."""

    id: str
    from_device_id: str
    from_port: str
    to_device_id: str
    to_port: str
