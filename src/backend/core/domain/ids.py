from __future__ import annotations

from uuid import UUID, uuid4


def new_id() -> UUID:
    return uuid4()


def parse_uuid(value: str | UUID) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(value)

