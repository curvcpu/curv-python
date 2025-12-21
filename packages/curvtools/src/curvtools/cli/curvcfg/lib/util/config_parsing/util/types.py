from enum import Enum
from typing import Any, Optional, List, Tuple
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
# Exported types
# ---------------------------------------------------------------------------

__all__ = [
    "Artifact", 
    "ValueSource", 
    "ParseType", 
    "_Domain", 
    "DomainChoices", 
    "DomainRange",
]

class Artifact(Enum):
    MK = "MK"
    ENV = "ENV"
    SVH = "SVH"
    SVPKG = "SVPKG"
    JINJA2 = "JINJA2"
    NONE = "NONE"  # used when artifacts = []


class ValueSource(Enum):
    CONSTANT = "CONSTANT"
    TOML     = "TOML"


class ParseType(Enum):
    STRING       = "string"
    INT          = "int"
    UINT         = "uint"
    OBJECT_ARRAY = "array[object]"
    @classmethod
    def from_str(cls, s: str) -> "ParseType":
        return cls(s)


DomainChoices = List[Any]
DomainRange = Tuple[int, int]


@dataclass(frozen=True)
class _Domain:
    kind: str  # "none", "choices", or "range"
    choices: Optional[DomainChoices] = None
    range: Optional[DomainRange] = None
    default: Optional[Any] = None
