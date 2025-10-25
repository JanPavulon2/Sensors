"""Enum conversion utilities"""

from typing import Any


class EnumHelper:
    """Helper to convert strings <-> Enum instances"""

    @staticmethod
    def to_enum(enum_class, value: Any):
        """Convert string or value to enum instance"""
        if isinstance(value, enum_class):
            return value
        if isinstance(value, str):
            try:
                return enum_class[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid enum value '{value}' for {enum_class.__name__}")
        raise TypeError(f"Expected str or {enum_class.__name__}, got {type(value)}")

    @staticmethod
    def to_name(value: Any) -> str:
        """Convert enum instance to string name"""
        if hasattr(value, "name"):
            return value.name
        return str(value)
