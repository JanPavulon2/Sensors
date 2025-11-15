"""Enum conversion utilities"""

from enum import Enum
from typing import TypeVar, Type, Optional, List, Any

# Generic type for any Enum subclass
E = TypeVar("E", bound=Enum)

class EnumHelper:
    """
    Utility class for working with Enums:
    - Convert enum members to strings (with case options)
    - Parse strings back to enum members (case-insensitive)
    - List all member names
    """

    @staticmethod
    def to_string(enum_value: E, lowercase: bool = False) -> str:
        """
        Convert Enum member to string (its name).

        Args:
            enum_value: Enum member
            lowercase: Return lowercase string (for config or tags)

        Returns:
            Enum member name as string
        """
        if not isinstance(enum_value, Enum):
            raise TypeError(f"Expected Enum, got {type(enum_value).__name__}")
        name = enum_value.name
        return name.lower() if lowercase else name
    
    @staticmethod
    def from_string(enum_class: Type[E], name: str, case_insensitive: bool = True,
                    default: Optional[E] = None) -> Optional[E]:
        """
        Parse string to Enum member.

        Args:
            enum_class: Enum class to parse into
            name: String name (case-insensitive by default)
            case_insensitive: If True, matches ignoring case
            default: Return value if not found (None = raise)

        Returns:
            Enum member or default if provided
        """
        if not issubclass(enum_class, Enum):
            raise TypeError(f"{enum_class} is not an Enum class")

        if case_insensitive:
            name = name.upper()

        for member in enum_class:
            if (member.name.upper() if case_insensitive else member.name) == name:
                return member

        if default is not None:
            return default
        raise ValueError(f"Invalid {enum_class.__name__} name: {name}")

    @staticmethod
    def list_names(enum_class: Type[E], lowercase: bool = False) -> List[str]:
        """
        List all Enum member names.

        Args:
            enum_class: Enum class to inspect
            lowercase: Return lowercase names

        Returns:
            List of member names (strings)
        """
        if not issubclass(enum_class, Enum):
            raise TypeError(f"{enum_class} is not an Enum class")

        if lowercase:
            return [member.name.lower() for member in enum_class]
        return [member.name for member in enum_class]

    @staticmethod
    def list_values(enum_class: Type[E]) -> List[Any]:
        """
        List all Enum member values (for Enums with custom .value).

        Args:
            enum_class: Enum class to inspect

        Returns:
            List of .value for all members
        """
        if not issubclass(enum_class, Enum):
            raise TypeError(f"{enum_class} is not an Enum class")

        return [member.value for member in enum_class]
    
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
